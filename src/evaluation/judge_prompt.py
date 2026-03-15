"""
Judge prompt template and parser.
LLM-as-judge evaluation logic.
"""

JUDGE_PROMPT_TEMPLATE = """You are an impartial evaluator for question-answering tasks. 
 
Your job is to evaluate whether the LLM answer correctly answers the question, 
based on the provided ground truth answer. 
 
Rules: 
- Focus on factual correctness and completeness. 
- Ignore differences in wording or style. 
- Do not reward unsupported extra information. 
- Do not penalize correct paraphrasing. 
 
Scoring rubric: 
5 = Fully correct and equivalent to the ground truth 
4 = Mostly correct, very minor omission or imprecision 
3 = Partially correct, missing key information 
2 = Mostly incorrect, only small correct elements 
1 = Completely incorrect or unrelated 
 
Question: 
{question} 
 
Ground truth answer: 
{answer} 
 
LLM answer: 
{llm_answer} 
 
Output exactly two lines: 
 
SCORE: <integer from 1 to 5> 
EXPLANATION: <brief explanation> 
"""


def parse_judge_response(response: str) -> tuple[int, str]:
    """
    Parse the judge's response to extract score and explanation.
    
    Args:
        response: Judge LLM output
        
    Returns:
        Tuple of (score, explanation)
    """
    lines = response.strip().split('\n')
    score = None
    explanation = ""
    
    for line in lines:
        if line.startswith('SCORE:'):
            try:
                score = int(line.split(':')[1].strip())
            except (ValueError, IndexError):
                score = 0
        elif line.startswith('EXPLANATION:'):
            explanation = line.split(':', 1)[1].strip()
    
    return score, explanation
