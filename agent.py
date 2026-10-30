import json, os, re, time, uuid
from datetime import datetime
from pathlib import Path
from retrieval import PolicyRetriever

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

class StudentSupportAgent:
    def __init__(self):
        self.records = json.loads((DATA/"students.json").read_text(encoding="utf-8"))
        self.retriever = PolicyRetriever(DATA/"student_policy.txt")
        self.memory_path = DATA/"memory.json"
        self.approvals_path = DATA/"approvals.json"
        self.audit_path = DATA/"audit.jsonl"
        self.memory = self._load_json(self.memory_path, {})
        self.approvals = self._load_json(self.approvals_path, [])
        self.tickets_path = DATA/"tickets.json"
        self.tickets = self._load_json(self.tickets_path, [])

    def _load_json(self, path, default):
        if not path.exists(): return default
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return default

    def _save(self, path, obj):
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

    def list_students(self): return list(self.records.keys())
    def student_name(self, sid): return self.records.get(sid, {}).get("name", "Unknown")

    def _audit(self, actor, action, target, allowed, approval, result, details=""):
        row = {"timestamp":datetime.now().isoformat(timespec="seconds"), "actor":actor,
               "action":action, "target":target, "allowed":bool(allowed),
               "approval_status":approval, "result":result, "details":details}
        with self.audit_path.open("a", encoding="utf-8") as f: f.write(json.dumps(row)+"\n")
        return row

    def get_audit_log(self):
        if not self.audit_path.exists(): return []
        rows=[]
        for line in self.audit_path.read_text(encoding="utf-8").splitlines()[-100:]:
            try: rows.append(json.loads(line))
            except Exception: pass
        return rows

    def get_memory(self, sid): return self.memory.get(sid, {})

    def _remember_safe_facts(self, sid, prompt):
        # Intentionally allow only a narrow, non-sensitive preference format.
        # Never persist raw chat text.
        m = re.search(r"\bmy preferred name is ([A-Za-z][A-Za-z -]{0,30})", prompt, re.I)
        if m:
            value=m.group(1).strip()
            if not re.search(r"\b(password|otp|pin|token|secret)\b", value, re.I):
                self.memory.setdefault(sid, {})["preferred_name"] = value
                self._save(self.memory_path, self.memory)
                return f"I'll remember your preferred name as {value}."
        return None

    def _sensitive_secret(self, prompt):
        # Detect likely OTP/password disclosures and avoid storing the message.
        return bool(re.search(r"\b(otp|password|passcode|one[- ]time password)\b", prompt, re.I))

    def _private_record(self, actor, target, field):
        if actor != target:
            self._audit(actor, "read_private_record", target, False, "not_required",
                        "blocked", f"Requested field: {field}")
            return None, "Access blocked: you can only view your own private student record."
        record=self.records.get(actor)
        if not record:
            self._audit(actor, "read_private_record", target, False, "not_required","failed","Unknown student")
            return None, "I couldn't find your student record."
        self._audit(actor, "read_private_record", target, True, "not_required","success",f"Field: {field}")
        return record, None

    def _queue_change(self, sid, prompt):
        # Do not perform the change here; create a pending approval only.
        req = {"request_id":"APR-"+uuid.uuid4().hex[:8].upper(), "student_id":sid,
               "action":"change_registered_phone", "summary":"Change registered phone number",
               "requested_value":"[REDACTED - demo does not store the supplied number]",
               "status":"pending", "created_at":datetime.now().isoformat(timespec="seconds")}
        self.approvals.append(req); self._save(self.approvals_path,self.approvals)
        self._audit(sid,"change_registered_phone",sid,True,"pending","not_executed",
                    "Sensitive change queued; value not persisted")
        return req

    def get_pending_approvals(self, sid):
        return [x for x in self.approvals if x["student_id"]==sid and x["status"]=="pending"]

    def decide_approval(self, request_id, approver_sid, approved):
        req=next((x for x in self.approvals if x["request_id"]==request_id),None)
        if not req: return "Approval request not found."
        if req["student_id"] != approver_sid:
            self._audit(approver_sid,"decide_approval",req["student_id"],False,"denied","blocked","Cannot approve another student's request")
            return "Blocked: you cannot approve another student's request."
        if req["status"] != "pending": return f"Request already {req['status']}."
        if approved:
            # Demo executes an approved action by recording a simulated completion.
            req["status"]="approved_executed"
            result="Approved. Demo action marked executed; no real phone number was changed."
            final="success_simulated"
        else:
            req["status"]="rejected"
            result="Rejected. The sensitive action was not executed."
            final="not_executed"
        req["decided_at"]=datetime.now().isoformat(timespec="seconds")
        self._save(self.approvals_path,self.approvals)
        self._audit(approver_sid,"decide_approval",req["student_id"],True,
                    "approved" if approved else "rejected",final,req["request_id"])
        return result

    def _create_ticket(self, sid, prompt):
        ticket={"ticket_id":"TKT-"+uuid.uuid4().hex[:8].upper(),"student_id":sid,
                "summary":"Student support request","status":"open",
                "created_at":datetime.now().isoformat(timespec="seconds")}
        self.tickets.append(ticket); self._save(self.tickets_path,self.tickets)
        self._audit(sid,"create_support_ticket",sid,True,"not_required","success",ticket["ticket_id"])
        return ticket

    def handle(self, prompt, sid):
        start=time.perf_counter()
        trace={"student_id":sid,"route":"unknown","tools":[],"retrieved_evidence":[],
               "permission_decision":"not_applicable","approval_status":"not_required",
               "token_usage":{"input_tokens":0,"output_tokens":0,
                              "note":"No LLM/API is used; model token usage is not applicable."}}
        if sid not in self.records:
            answer="Please sign in with a valid demo student account."
            trace["route"]="authentication"
        else:
            # Sensitive chat disclosures are never added to persistent memory.
            if self._sensitive_secret(prompt):
                self._audit(sid,"sensitive_secret_detected",sid,True,"not_required","not_stored",
                            "Sensitive chat content was not persisted")
                answer="For your safety, don't share passwords or OTPs in chat. I have not saved this message to long-term memory."
                trace["route"]="sensitive_input_filter"
            else:
                remembered=self._remember_safe_facts(sid,prompt)
                if remembered:
                    answer=remembered; trace["route"]="memory_write"; trace["tools"].append("safe_memory")
                elif re.search(r"\b(change|update|modify)\b.*\b(phone|mobile|email|address)\b",prompt,re.I):
                    req=self._queue_change(sid,prompt)
                    answer=f"Approval required. I created request **{req['request_id']}**. Nothing has been changed yet. Use the Human approval queue to approve or reject it."
                    trace["route"]="sensitive_action"; trace["tools"].append("request_sensitive_change")
                    trace["approval_status"]="pending"; trace["permission_decision"]="allowed_to_request_not_execute"
                elif re.search(r"\b(other student|another student|student\s+[A-Z0-9_-]+)\b",prompt,re.I):
                    target_match=re.search(r"\b(student\s+)?([A-Z]\d{2,}|S\d{2,})\b",prompt,re.I)
                    target=target_match.group(2).upper() if target_match else next((x for x in self.records if x != sid), "UNKNOWN")
                    field="scholarship" if "scholar" in prompt.lower() else "fee"
                    _,error=self._private_record(sid,target,field)
                    answer=error or "Access blocked."
                    trace["route"]="authorization_check"; trace["tools"].append("student_record_tool")
                    trace["permission_decision"]="denied"
                elif "fee" in prompt.lower() and any(w in prompt.lower() for w in ["status","paid","due","my"]):
                    rec,error=self._private_record(sid,sid,"fee_status")
                    answer=error or f"Your fee status is **{rec['fee_status']}**."
                    trace["route"]="tool_call"; trace["tools"].append("get_fee_status")
                    trace["permission_decision"]="allowed"
                elif "scholar" in prompt.lower():
                    rec,error=self._private_record(sid,sid,"scholarship_status")
                    answer=error or f"Your scholarship status is **{rec['scholarship_status']}**."
                    trace["route"]="tool_call"; trace["tools"].append("get_scholarship_status")
                    trace["permission_decision"]="allowed"
                elif any(w in prompt.lower() for w in ["support request","raise a ticket","create a ticket","portal failed"]):
                    ticket=self._create_ticket(sid,prompt)
                    chunks=self.retriever.retrieve(prompt)
                    trace["route"]="tool_and_retrieval"; trace["tools"].append("create_support_ticket")
                    trace["retrieved_evidence"]=[c["id"] for c in chunks]
                    answer=f"I created support ticket **{ticket['ticket_id']}**. Status: {ticket['status']}."
                    if chunks: answer += "\n\nRelevant policy: " + " ".join(c["text"] for c in chunks)
                else:
                    chunks=self.retriever.retrieve(prompt)
                    trace["route"]="policy_retrieval" if chunks else "fallback"
                    trace["retrieved_evidence"]=[c["id"] for c in chunks]
                    if chunks:
                        answer="Here is the relevant student policy information:\n\n" + "\n\n".join(c["text"] for c in chunks)
                    else:
                        answer="I don't have enough information in the sample student policy to answer confidently. Please contact the student support office."
        trace["latency_ms"]=round((time.perf_counter()-start)*1000,2)
        # Simple local word-based estimate; not model API token accounting.
        trace["token_usage"]["estimated_input_words"]=len(prompt.split())
        trace["token_usage"]["estimated_output_words"]=len(answer.split())
        trace["answer_length_words"]=len(answer.split())
        return {"answer":answer,"trace":trace}
