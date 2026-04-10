"""
question_bank.py
================
Builds and queries the question bank with sub_domain filtering.
Solves the Angular-vs-React problem: candidates only get questions
relevant to their specific tech stack, not the whole domain bucket.

Usage:
    from question_bank import QuestionBank
    qb = QuestionBank('interview_dataset_v4.csv', 'skill_taxonomy_v2.csv')
    q  = qb.get_next_question('System Design', 'web_frontend', 'Medium', asked_set)
"""

import pandas as pd
import random
import re
from typing import Optional, Set


class QuestionBank:

    def __init__(self, dataset_path: str, taxonomy_path: str):
        self.df       = self._load(dataset_path)
        self.taxonomy = self._load_taxonomy(taxonomy_path)
        self.bank     = self._build_bank()

    # ── LOAD ──────────────────────────────────────────────────
    def _load(self, path: str) -> pd.DataFrame:
        if path.endswith('.json'):
            df = pd.read_json(path, lines=True)
        else:
            df = pd.read_csv(path)
            
        df['ideal_answer'] = df['ideal_answer'].fillna('')
        
        if 'sub_domain' not in df.columns:
            df['sub_domain'] = df.get('primary_tag', 'general')
            
        df['sub_domain']   = df['sub_domain'].fillna('general')
        return df

    def _load_taxonomy(self, path: str) -> dict:
        """Returns {skill_name_lower: (domain, sub_domain)}"""
        tx = pd.read_csv(path)
        return {
            row['skill'].lower(): (row['domain'], row['sub_domain'])
            for _, row in tx.iterrows()
        }

    def _build_bank(self) -> dict:
        """
        bank = {
            skill: {
                sub_domain: {
                    difficulty: [ {question, golden_answer, keywords, difficulty} ]
                }
            }
        }
        """
        bank = {}
        seen = set()
        q_df = self.df.drop_duplicates(subset=['question'])

        for _, row in q_df.iterrows():
            skill      = row['skill']
            sub_domain = row.get('sub_domain', 'general')
            difficulty = row.get('difficulty', 'Medium')
            question   = row['question']
            ideal      = row['ideal_answer']

            key = (skill, sub_domain, question)
            if key in seen:
                continue
            seen.add(key)

            entry = {
                'question':      question,
                'golden_answer': ideal,
                'keywords':      self._extract_keywords(ideal),
                'difficulty':    difficulty,
                'sub_domain':    sub_domain,
            }
            (bank
             .setdefault(skill, {})
             .setdefault(sub_domain, {})
             .setdefault(difficulty, [])
             .append(entry))

        return bank

    @staticmethod
    def _extract_keywords(text: str, n: int = 8) -> list:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        stop  = {'this','that','with','from','have','been','they','them','when',
                 'will','also','more','into','than','then','over','used','uses',
                 'which','where','while','their','there','these','those','your',
                 'like','such','only','some','data','make','made','allows','means'}
        freq  = {}
        for w in words:
            if w not in stop:
                freq[w] = freq.get(w, 0) + 1
        return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])][:n]

    # ── PUBLIC API ─────────────────────────────────────────────
    def map_resume_skill(self, resume_skill: str) -> tuple:
        """
        Maps a resume skill to (domain, sub_domain).
        Returns ('Unknown', 'general') if not found.
        """
        return self.taxonomy.get(resume_skill.lower(), ('Unknown', 'general'))

    def get_profile(self, resume_skills: list) -> dict:
        """
        Given resume skill list, returns a domain profile:
        { domain: [sub_domain, ...], ... }
        Angular, React → System Design: [web_frontend]
        PyTorch, TensorFlow → ML: [dl_frameworks]
        MySQL, MongoDB → DBMS: [relational, nosql]
        """
        profile = {}
        for skill in resume_skills:
            domain, sub_domain = self.map_resume_skill(skill)
            if domain != 'Unknown':
                profile.setdefault(domain, set()).add(sub_domain)
        return {d: list(subs) for d, subs in profile.items()}

    def get_next_question(
        self,
        skill:       str,
        difficulty:  str,
        asked:       Set[str],
        sub_domain:  Optional[str] = None,
    ) -> Optional[dict]:
        """
        Returns a fresh question for skill + difficulty.
        If sub_domain provided, filters to that sub_domain first.
        Falls back to other sub_domains if sub_domain exhausted.
        Falls back to other difficulties if all exhausted.
        """
        skill_bank = self.bank.get(skill, {})
        if not skill_bank:
            return None

        def get_fresh(pool):
            fresh = [q for q in pool if q['question'] not in asked]
            return random.choice(fresh) if fresh else None

        # Try preferred sub_domain + exact difficulty
        if sub_domain and sub_domain in skill_bank:
            pool = skill_bank[sub_domain].get(difficulty, [])
            q = get_fresh(pool)
            if q:
                return q

        # Try preferred sub_domain + any difficulty
        if sub_domain and sub_domain in skill_bank:
            all_qs = [q for qs in skill_bank[sub_domain].values() for q in qs]
            q = get_fresh(all_qs)
            if q:
                return q

        # Try any sub_domain + exact difficulty
        all_diff = [q for sd in skill_bank.values()
                    for q in sd.get(difficulty, [])]
        q = get_fresh(all_diff)
        if q:
            return q

        # Try any sub_domain + any difficulty
        all_qs = [q for sd in skill_bank.values()
                  for qs in sd.values() for q in qs]
        q = get_fresh(all_qs)
        if q:
            return q

        # Last resort: allow repeat from sub_domain
        pool = list(skill_bank.get(sub_domain or list(skill_bank.keys())[0],
                                   {}).get(difficulty, []))
        return random.choice(pool) if pool else None

    def available_skills(self) -> list:
        return sorted(self.bank.keys())

    def stats(self) -> dict:
        out = {}
        for skill, sub_domains in self.bank.items():
            total = sum(len(qs) for sd in sub_domains.values()
                        for qs in sd.values())
            out[skill] = {
                'total_questions': total,
                'sub_domains':     {
                    sd: sum(len(qs) for qs in diffs.values())
                    for sd, diffs in sub_domains.items()
                }
            }
        return out


# ── QUICK TEST ────────────────────────────────────────────────
if __name__ == '__main__':
    qb = QuestionBank('/home/claude/interview_dataset_v4.csv',
                      '/home/claude/skill_taxonomy_v2.csv')

    print("=== Question Bank Stats ===")
    for skill, info in qb.stats().items():
        print(f"\n  {skill} ({info['total_questions']} Q):")
        for sd, count in info['sub_domains'].items():
            print(f"    {sd:<25} {count} Q")

    print("\n=== Resume Skill Mapping ===")
    resume = ['Angular', 'TypeScript', 'React', 'Node.js', 'Docker',
              'PyTorch', 'MySQL', 'MongoDB', 'Python', 'Django']
    for skill in resume:
        domain, sub = qb.map_resume_skill(skill)
        print(f"  {skill:<15} → {domain:<16} / {sub}")

    print("\n=== Domain Profile from Resume ===")
    profile = qb.get_profile(resume)
    for domain, subs in profile.items():
        print(f"  {domain:<16}: {subs}")

    print("\n=== get_next_question Tests ===")
    asked = set()

    # Angular person should get web_frontend question, not CAP theorem
    q = qb.get_next_question('System Design', 'Medium', asked, sub_domain='web_frontend')
    if q:
        print(f"\n  Angular user → sub_domain=web_frontend:")
        print(f"    Q: {q['question']}")
        print(f"    sub_domain: {q['sub_domain']}")
        asked.add(q['question'])

    # Generic SD person gets core SD question
    q = qb.get_next_question('System Design', 'Medium', asked, sub_domain='system_design_core')
    if q:
        print(f"\n  Generic SD user → sub_domain=system_design_core:")
        print(f"    Q: {q['question']}")
        print(f"    sub_domain: {q['sub_domain']}")

    # HR question
    q = qb.get_next_question('HR', 'Medium', set(), sub_domain='hr_behavioral')
    if q:
        print(f"\n  HR → sub_domain=hr_behavioral:")
        print(f"    Q: {q['question']}")

def get_next_question(skill: str, sub_domain: str, difficulty: str, asked: list) -> dict:
    from pathlib import Path
    base_dir = Path(__file__).parent
    dataset_path = str(base_dir.parent / 'AI-Driven-Adaptive-Mock-Interview-Platform' / 'interview_dataset_v10_FINAL.json')
    taxonomy_path = str(base_dir / 'skill_taxonomy_v2.csv')
    qb = QuestionBank(dataset_path, taxonomy_path)
    # The asked parameter needs to be a set per QuestionBank signature
    return qb.get_next_question(skill=skill, difficulty=difficulty, asked=set(asked), sub_domain=sub_domain)
