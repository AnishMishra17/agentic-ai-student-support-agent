import json, time
from agent import StudentSupportAgent

def main():
    agent=StudentSupportAgent()
    tests=[
      ("S001","What is my current fee status?","fee status"),
      ("S001","What is my scholarship status?","scholarship"),
      ("S001","The payment portal failed. Can I pay on the next working day?","policy"),
      ("S001","Please create a support request for my payment portal error","ticket"),
      ("S001","My preferred name is Sam","memory"),
      ("S001","What is the official bus route number?","fallback"),
      ("S001","My OTP is 123456, please remember it","secret"),
    ]
    rows=[]
    for sid,q,expected in tests:
        result=agent.handle(q,sid); ans=result["answer"].lower(); tr=result["trace"]
        if expected=="fee status": passed="fee status" in ans
        elif expected=="scholarship": passed="scholarship status" in ans
        elif expected=="policy": passed=bool(tr["retrieved_evidence"])
        elif expected=="ticket": passed="created support ticket" in ans
        elif expected=="memory": passed="remember" in ans
        elif expected=="fallback": passed="don't have enough information" in ans
        elif expected=="secret": passed="not saved" in ans
        rows.append({"question":q,"expected":expected,"passed":bool(passed),"route":tr["route"],
                     "tools":", ".join(tr["tools"]),"latency_ms":tr["latency_ms"],
                     "estimated_input_words":tr["token_usage"]["estimated_input_words"],
                     "estimated_output_words":tr["token_usage"]["estimated_output_words"],
                     "retrieved_evidence":", ".join(tr["retrieved_evidence"])})
    with open("assignment1_evaluation_results.json","w",encoding="utf-8") as f: json.dump(rows,f,indent=2)
    print(f"Passed: {sum(r['passed'] for r in rows)}/{len(rows)} ({sum(r['passed'] for r in rows)/len(rows)*100:.1f}%)")
    print("Mean latency (ms):",round(sum(r["latency_ms"] for r in rows)/len(rows),2))
    print("LLM API token usage: N/A (no LLM API; estimated word counts are provided)")
    print("Saved assignment1_evaluation_results.json")
    for r in rows: print(("PASS" if r["passed"] else "FAIL"),"|",r["expected"],"|",r["route"],"|",r["question"])
if __name__=="__main__": main()
