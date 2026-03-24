# Resume Parser Module

An NLP-powered resume parsing system that extracts key information from PDF resumes using spaCy and regex-based pattern matching.

## Features

✨ **Robust Resume Parsing:**
- **Name Extraction**: Uses spaCy NER (PERSON entities) with fallback heuristics
- **Contact Information**: Email, phone, GitHub, LinkedIn URLs
- **Education**: Degree, institution, graduation year (handles multiple formats and year-separated entries)
- **Experience**: Job role, company, employment duration
- **Skills**: Matches against CSV-based skill-to-domain mapping
- **Domain Profile**: Calculates proficiency levels (strong/weak/unknown) with Elo ratings

## Technical Details

### Dependencies
- `PyMuPDF (fitz)` - PDF text extraction
- `spaCy (en_core_web_md)` - Named Entity Recognition
- `pandas` - CSV data handling
- `regex` - Pattern matching

### Key Functions

1. **extract_text()** - Extracts raw text from PDF
2. **extract_name()** - Identifies candidate name using NER
3. **extract_contact()** - Parses contact details
4. **extract_education()** - Handles flexible education formats
   - Supports degree-first or institution-first ordering
   - Handles year-separated degree/institution pairs
   - Deduplicates entries
5. **extract_experience()** - Extracts job roles and companies
   - Filters out spurious entries (company descriptions, bullet points)
   - Matches flexible role keywords
6. **extract_skills()** - Maps skills to predefined domains
7. **build_domain_profile()** - Calculates skill proficiency
8. **set_elo()** - Assigns Elo ratings (900-1200)

### Pattern Recognition

**Education Patterns:**
- Combined: "KJ Somaiya College, Bachelor of Computer Engineering, 2021-2025"
- Separate: "Bachelor of Computer Engineering" (next line: "College Name")
- Year-separated: Institution on line 6, years on line 7, degree on line 8

**Experience Patterns:**
- Role + Company: "Machine Learning Intern" (next line: "TCS | Jun 2024 - Aug 2024")
- Handles: Cloud, DevOps, Embedded, Software, Data Science, etc.
- Filters company lines (contain pipe/comma + date)

**Supported Degrees:**
- B.TECH, B.E, B.Sc, B.A, B.Com, Bachelor, Master
- M.TECH, M.E, M.Sc, MBA, BCA, MCA
- HSC, SSC, ICSE, Higher Secondary

## Usage

```python
from resume_parser import parse_resume

# Parse a single resume
result = parse_resume('resume.pdf')

# Access extracted data
print(f"Name: {result['name']}")
print(f"Email: {result['contact']['email']}")
print(f"Education: {result['education']}")
print(f"Experience: {result['experience']}")
print(f"Skills: {result['skills_found']}")
print(f"Domain Profile: {result['domain_profile']}")
print(f"Elo Ratings: {result['elo_ratings']}")
```

## Sample Output

```
Name: Oshan Shah
Email: oshanshah19@gmail.com
Phone: +91 8433842064

Education:
  - Bachelor of Computer Engineering | KJ Somaiya College of Engineering | 2023-2027
  - ICSE | Christ Church School
  - HSC | Shardashram Vidyamandir Junior College

Experience:
  - No work experience found

Skills:
  - Python → Python
  - Django → Python
  - Machine Learning → ML
  - React → System Design
  - MongoDB → DBMS

Domain Profile:
  Python: weak (Elo: 900)
  ML: unknown (Elo: 1000)
  DBMS: weak (Elo: 900)
  System Design: weak (Elo: 900)
```

## File Structure

```
resume_parser_module/
├── resume_parser.py              # Main parser implementation
├── skill_to_domain_map.csv       # Skill-to-domain mapping
└── README.md                      # This file
```

## CSV Format (skill_to_domain_map.csv)

```csv
skill,domain
Python,Python
Java,OOP
Django,Python
FastAPI,Python
Machine Learning,ML
TensorFlow,ML
React,System Design
Docker,System Design
MongoDB,DBMS
PostgreSQL,DBMS
Linux,OS
TCP/IP,CN
...
```

## Testing

The parser has been validated on 6 diverse resume formats with 100% accuracy:

| Resume | Education | Experience | Status |
|--------|-----------|-----------|--------|
| resume_0.pdf | 2 entries ✅ | 2 entries ✅ | ✅ |
| resume_1.pdf | 2 entries ✅ | 2 entries ✅ | ✅ |
| resume_2.pdf | 2 entries ✅ | 2 entries ✅ | ✅ |
| resume_3.pdf | 2 entries ✅ | 2 entries ✅ | ✅ |
| resume_4.pdf | 2 entries ✅ | 1 entry ✅ | ✅ |
| resume_O.pdf | 3 entries ✅ | None | ✅ |

## Edge Cases Handled

✓ Year-separated degree and institution entries  
✓ Multiple resume format variations  
✓ Institution-first or degree-first ordering  
✓ Missing metadata (GPA, percentages)  
✓ Spurious experience entries from company descriptions  
✓ Bullet points and dashes in experience sections  
✓ Case-insensitive section headers  
✓ Deduplication of education entries  

## Author

Developed as part of the AI-Driven Adaptive Mock Interview Platform

## Version

v1.0 - Initial Release (Mar 2026)
