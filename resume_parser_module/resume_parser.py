import fitz
import spacy
import pandas as pd
import re
from collections import Counter
from spacy.matcher import PhraseMatcher

nlp = spacy.load("en_core_web_md")

# ── 1. Extract raw text ─────────────────────────────────────────
def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc).strip()

# ── 2. Extract name ─────────────────────────────────────────────
def extract_name(text: str) -> str:
    doc = nlp(text[:500])
    
    # First, try to find PERSON named entity
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    
    # Fallback: get the first line that looks like a name (short, capitalized)
    for line in text.splitlines():
        line = line.strip()
        if line and len(line.split()) >= 2 and len(line.split()) <= 4:
            # Check if it starts with capital letters (likely a name)
            if line[0].isupper() and all(word[0].isupper() or not word.isalpha() for word in line.split()):
                # Exclude common section headers
                if not any(keyword in line.lower() for keyword in ['education', 'experience', 'skills', 'projects', 'contact']):
                    return line
    
    return "Not found"

# ── 3. Extract contact ──────────────────────────────────────────
def extract_contact(text: str) -> dict:
    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    phone = re.search(r'(\+91[\s\-]?\d{10}|\b[6-9]\d{9}\b)', text)
    linkedin = re.search(r'linkedin\.com/in/[\w\-]+', text, re.IGNORECASE)
    github = re.search(r'github\.com/[\w\-]+', text, re.IGNORECASE)

    return {
        "email": email.group(0) if email else "Not found",
        "phone": phone.group(0) if phone else "Not found",
        "linkedin": linkedin.group(0) if linkedin else "Not found",
        "github": github.group(0) if github else "Not found"
    }

# ── 4. Extract education ───────────────────────────────────────
def extract_education(text: str) -> list:
    education = []
    # Look for "Education" section with flexible case matching
    edu_section = re.search(r'(?:^|\n)(?:Education|EDUCATION)(?:\s*\n|\s*:)?(.*?)(?=\n(?:Experience|EXPERIENCE|Projects|PROJECTS|Skills|SKILLS|Work|WORK|Technical|TECHNICAL|Involvement))', text, re.DOTALL | re.MULTILINE | re.IGNORECASE)

    if not edu_section:
        return []

    edu_text = edu_section.group(1).strip()
    lines = [l.strip() for l in edu_text.split('\n') if l.strip()]
    
    seen_entries = set()
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Skip only if line is PURELY metadata (bullets, percentages, GPA values, test scores, etc.)
        # But NOT if it contains an institution name along with metadata
        if line.startswith('•'):
            i += 1
            continue
        
        # Only skip if it's JUST metadata without institution/degree
        if ('GPA' in line or 'Percentage' in line or 'CGPA' in line or 'JEE' in line or 'percentile' in line) and not re.search(r'(?:College|University|Institute|School|Academy|Vidyalaya|-)', line, re.IGNORECASE):
            i += 1
            continue
        
        # Skip percentage lines without degree/institution
        if '(' in line and ')' in line and '%' in line and not re.search(r'(?:College|University|Institute|School|Academy|Vidyalaya)|B\.?TECH|B\.E|B\.Sc|B\.A|B\.Com|Bachelor|Master|M\.?TECH|M\.E|M\.Sc|MBA|BCA|MCA|HSC|SSC|ICSE', line, re.IGNORECASE):
            i += 1
            continue
        
        degree = "Not found"
        institution = "Not found"
        year = "Not found"
        
        # Check if current line has degree or institution
        has_degree = bool(re.search(r'\b(B\.?TECH|B\.E|B\.Sc|B\.A|B\.Com|Bachelor|Master|M\.?TECH|M\.E|M\.Sc|MBA|BCA|MCA|HSC|SSC|Higher\s+Secondary|ICSE)\b', line, re.IGNORECASE))
        has_institution = bool(re.search(r'(?:College|University|Institute|School|Academy|Vidyalaya|-\s+[A-Z])', line, re.IGNORECASE))
        
        # Handle case where institution and degree are on same line (e.g., "KJ Somaiya College of Engineering, Bachelor of Computer Engineering")
        if has_institution and has_degree:
            # Extract degree
            degree_match = re.search(r'\b(B\.?TECH|B\.E|B\.Sc|B\.A|B\.Com|Bachelor|Master|M\.?TECH|M\.E|M\.Sc|MBA|BCA|MCA|HSC|SSC|Higher\s+Secondary|ICSE)\b(?:\s+(?:of|in)\s+[A-Za-z\s&]+)?', line, re.IGNORECASE)
            if degree_match:
                degree = degree_match.group(0)
                degree = re.sub(r'\s+$', '', degree)
            
            # Extract institution - everything up to the degree or dash
            inst_match = re.search(r'^([A-Za-z\s&\.\,\(\)]+?)(?:\s*[,\-]\s*(?:Bachelor|Master|B\.?TECH|B\.E|B\.Sc|M\.?TECH|M\.E|M\.Sc))', line, re.IGNORECASE)
            if inst_match:
                institution = inst_match.group(1).strip()
            else:
                # Try extracting up to pipe
                inst_match = re.search(r'^([A-Za-z\s&\.\,\(\)]*?(?:College|University|Institute|School|Academy|Vidyalaya)[A-Za-z0-9\s&\.\,\(\)]*?)(?:\||,|$)', line, re.IGNORECASE)
                if inst_match:
                    institution = inst_match.group(1).strip()
            
            # Extract year from current or next line
            year_match = re.search(r'(\d{4}\s*[–-]\s*\d{4}|\w+\s+\d{4}\s*[–-]\s*\d{4})', line)
            if year_match:
                year = year_match.group(0)
            elif i + 1 < len(lines):
                next_line = lines[i + 1]
                yr_match = re.search(r'(\d{4}\s*[–-]\s*\d{4}|\w+\s+\d{4}\s*[–-]\s*\d{4})', next_line)
                if yr_match:
                    year = yr_match.group(0)
        
        elif has_degree:
            # Extract degree with optional field
            degree_match = re.search(r'\b(B\.?TECH|B\.E|B\.Sc|B\.A|B\.Com|Bachelor|Master|M\.?TECH|M\.E|M\.Sc|MBA|BCA|MCA|HSC|SSC|Higher\s+Secondary|ICSE)\b(?:\s+(?:of|in)\s+[A-Za-z\s&]+)?', line, re.IGNORECASE)
            if degree_match:
                degree = degree_match.group(0)
                degree = re.sub(r'\s+$', '', degree)
            
            # Extract year from current line
            year_match = re.search(r'(\d{4}\s*[–-]\s*\d{4}|\w+\s+\d{4}\s*[–-]\s*\w+\s+\d{4})', line)
            if year_match:
                year = year_match.group(0)
            
            # Look in next line for institution
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Check if next line has institution keyword OR is a 3+ letter acronym like "NIT", "IIT"
                if re.search(r'(?:College|University|Institute|School|Academy|Vidyalaya)', next_line, re.IGNORECASE) or re.search(r'^[A-Z]{3,}\s+[A-Z]', next_line):
                    inst_match = re.search(r'^([A-Za-z\s&\.\,\(\)]*?(?:College|University|Institute|School|Academy|Vidyalaya|[A-Z]{3,})[A-Za-z0-9\s&\.\,\(\)]*?)(?:\||,|$|–)', next_line, re.IGNORECASE)
                    if inst_match:
                        institution = inst_match.group(1).strip()
                        # Also extract year from next line if not found
                        if year == "Not found":
                            yr_match = re.search(r'(\d{4}\s*[–-]\s*\d{4}|\w+\s+\d{4}\s*[–-]\s*\w+\s+\d{4})', next_line)
                            if yr_match:
                                year = yr_match.group(0)
                                
        elif has_institution:
            # Institution found, look in previous line for degree
            if i > 0:
                prev_line = lines[i - 1]
                if re.search(r'\b(B\.?TECH|B\.E|B\.Sc|B\.A|B\.Com|Bachelor|Master|M\.?TECH|M\.E|M\.Sc|MBA|BCA|MCA|HSC|SSC|Higher\s+Secondary|ICSE)\b', prev_line, re.IGNORECASE):
                    deg_match = re.search(r'\b(B\.?TECH|B\.E|B\.Sc|B\.A|B\.Com|Bachelor|Master|M\.?TECH|M\.E|M\.Sc|MBA|BCA|MCA|HSC|SSC|Higher\s+Secondary|ICSE)\b(?:\s+(?:of|in)\s+[A-Za-z\s&]+)?', prev_line, re.IGNORECASE)
                    if deg_match:
                        degree = deg_match.group(0)
                        degree = re.sub(r'\s+$', '', degree)
            
            # Check next 2 lines for degree if not found in previous (handles year-separated entries)
            if degree == "Not found":
                for j in range(i + 1, min(i + 3, len(lines))):
                    next_line = lines[j]
                    if re.search(r'\b(B\.?TECH|B\.E|B\.Sc|B\.A|B\.Com|Bachelor|Master|M\.?TECH|M\.E|M\.Sc|MBA|BCA|MCA|HSC|SSC|Higher\s+Secondary|ICSE)\b', next_line, re.IGNORECASE):
                        deg_match = re.search(r'\b(B\.?TECH|B\.E|B\.Sc|B\.A|B\.Com|Bachelor|Master|M\.?TECH|M\.E|M\.Sc|MBA|BCA|MCA|HSC|SSC|Higher\s+Secondary|ICSE)\b(?:\s+(?:of|in)\s+[A-Za-z\s&]+)?', next_line, re.IGNORECASE)
                        if deg_match:
                            degree = deg_match.group(0)
                            degree = re.sub(r'\s+$', '', degree)
                            break
            
            # Extract institution
            inst_match = re.search(r'^([A-Za-z\s&\.\,\(\)]*?(?:College|University|Institute|School|Academy|Vidyalaya)[A-Za-z0-9\s&\.\,\(\)]*?)(?:\||,|$|–)', line, re.IGNORECASE)
            if inst_match:
                institution = inst_match.group(1).strip()
            
            # Extract year
            year_match = re.search(r'(\d{4}\s*[–-]\s*\d{4}|\w+\s+\d{4}\s*[–-]\s*\w+\s+\d{4})', line)
            if year_match:
                year = year_match.group(0)
        
        # Store entry if valid and not duplicate
        if degree != "Not found" and institution != "Not found":
            entry_key = (degree, institution, year)
            if entry_key not in seen_entries:
                education.append({
                    "degree": degree,
                    "institution": institution,
                    "year": year
                })
                seen_entries.add(entry_key)
        
        i += 1

    return education

# ── 5. Extract experience ──────────────────────────────────────
def extract_experience(text: str) -> list:
    experience = []
    # Look for "Experience" section - flexible case matching
    exp_section = re.search(r'(?:^|\n)(?:Experience|EXPERIENCE)(?:\s*\n|\s*:)?(.*?)(?=\n(?:Projects|PROJECTS|Skills|SKILLS|Technical|TECHNICAL|Involvement|Involvement|Certifications))', text, re.DOTALL | re.MULTILINE | re.IGNORECASE)

    if not exp_section:
        # No experience section found - return empty experience list
        return []

    exp_text = exp_section.group(1).strip()
    lines = [l.strip() for l in exp_text.split('\n') if l.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip bullet points and metadata lines
        if line.startswith('•') or line.startswith('–') or line.startswith('-') or line.startswith('I '):
            i += 1
            continue
        
        # Check if line contains a job role keyword (more flexible matching)
        # But exclude lines that look like company descriptions (contain pipe/comma + date, or end with parenthesized info + pipe/comma)
        # Company lines: "Company Name | Date" or "Company Name (location), Date" etc
        is_company_line = bool(re.search(r'(\||\,)\s*\w+\s+\d{4}\s*[–-]', line))
        
        if not is_company_line:
            role_match = re.search(
                r'(.*?(?:Machine Learning|Web Development|Software|Data Science|Data|DevOps|Cloud|Embedded|'
                r'Intern|Engineer|Developer|Scientist|Analyst|Manager|Consultant|Architect|Trainee).*)',
                line, re.IGNORECASE
            )
        else:
            role_match = None
        
        if role_match:
            role = line.strip()  # Take the whole first line as the role
            company = "Not found"
            duration = "Not found"
            
            # Look in next line (usually contains company and duration)
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                
                # Extract company (usually before comma or parenthesis)
                company_match = re.search(
                    r'^([A-Z][A-Za-z0-9\s&\.]+?)(?:\s*\(|,)',
                    next_line
                )
                if company_match:
                    company = company_match.group(1).strip()
                
                # Extract duration (Month Year - Month Year)
                duration_match = re.search(r'(\w+\s\d{4}\s*[–-]\s*\w+\s\d{4})', next_line)
                if duration_match:
                    duration = duration_match.group(0)
            
            experience.append({
                "role": role,
                "company": company,
                "duration": duration
            })
        
        i += 1

    return experience

# ── 6. Load skill map ──────────────────────────────────────────
def load_skill_map(csv_path: str = "skill_to_domain_map.csv") -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.lower()
    return df

# ── 7. Extract skills (section-based) ──────────────────────────
def extract_skills(text: str, skill_map: pd.DataFrame) -> list:
    skills_section = re.search(r'TECHNICAL SKILLS(.*?)(?=PROJECTS|EDUCATION|EXPERIENCE|$)', text, re.DOTALL | re.IGNORECASE)
    if skills_section:
        text = skills_section.group(1)

    doc = nlp(text)

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill.lower()) for skill in skill_map["skill"]]
    matcher.add("SKILLS", patterns)

    matches = matcher(doc)
    matched_skills = set()

    for _, start, end in matches:
        matched_skills.add(doc[start:end].text.lower())

    found = []
    for _, row in skill_map.iterrows():
        if row["skill"].lower() in matched_skills:
            found.append({
                "skill": row["skill"],
                "domain": row["domain"]
            })

    return found

# ── 8. Domain profile ──────────────────────────────────────────
def build_domain_profile(skills_found: list) -> dict:
    counts = Counter(s["domain"] for s in skills_found)

    all_domains = ["Python", "DSA", "OOP", "OS", "DBMS",
                   "CN", "System Design", "ML", "HR"]

    return {
        d: "strong" if counts.get(d, 0) >= 4
           else "weak" if counts.get(d, 0) >= 2
           else "unknown"
        for d in all_domains
    }

# ── 9. Elo scoring ─────────────────────────────────────────────
def set_elo(profile: dict) -> dict:
    return {
        d: 1200 if s == "strong" else 900 if s == "weak" else 1000
        for d, s in profile.items()
    }

# ── 10. Full pipeline ──────────────────────────────────────────
def parse_resume(pdf_path: str) -> dict:
    skill_map = load_skill_map()
    text = extract_text(pdf_path)

    name = extract_name(text)
    contact = extract_contact(text)
    education = extract_education(text)
    experience = extract_experience(text)
    skills = extract_skills(text, skill_map)
    profile = build_domain_profile(skills)
    elo = set_elo(profile)

    print(f"\n Name:    {name}")
    print(f" Email:   {contact['email']}")
    print(f" Phone:   {contact['phone']}")
    print(f" GitHub:  {contact['github']}")
    print(f" LinkedIn: {contact['linkedin']}")

    print("\n── Education ──")
    for e in education:
        year_str = f" | {e['year']}" if e['year'] != "Not found" else ""
        print(f"  {e['degree']} | {e['institution']}{year_str}")

    print("\n── Experience ──")
    if experience:
        for e in experience:
            duration_str = f" ({e['duration']})" if e['duration'] != "Not found" else ""
            print(f"  {e['role']} at {e['company']}{duration_str}")
    else:
        print("  No work experience found")

    print("\n── Skills found ──")
    for s in skills:
        print(f"  {s['skill']:<20} → {s['domain']}")

    print("\n── Domain profile ──")
    for domain, strength in profile.items():
        print(f"  {domain:<15} {strength:<8}  Elo: {elo[domain]}")

    return {
        "name": name,
        "contact": contact,
        "education": education,
        "experience": experience,
        "skills_found": skills,
        "domain_profile": profile,
        "elo_ratings": elo
    }

if __name__ == "__main__":
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else "resume.pdf"
    parse_resume(pdf)
