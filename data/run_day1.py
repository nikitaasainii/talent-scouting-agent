import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.jd_parser import JDParserAgent
from agents.github_discovery import GitHubDiscoveryAgent
from data.seed_chromadb import seed_from_candidates

sample_jd = """
We're hiring a Senior Backend Engineer for our fintech startup in Bangalore.

Requirements:
- 4+ years with Python and FastAPI
- Strong PostgreSQL and Redis experience
- AWS (EC2, S3, Lambda)
- Docker and Kubernetes
- Nice to have: Kafka, GraphQL

Full-time hybrid role. Remote candidates considered for exceptional profiles.
"""

print("=" * 60)
print("TALENT SCOUT AGENT — DAY 1 PIPELINE TEST")
print("=" * 60)

# Stage 1: Parse JD
print("\n[STAGE 1] JD Parsing")
parser = JDParserAgent()
parsed_jd, trace = parser.run(sample_jd)
for log in trace:
    print(log)

# Stage 2: GitHub Discovery
print("\n[STAGE 2] GitHub Candidate Discovery")
discovery = GitHubDiscoveryAgent()
candidates, trace = discovery.run(parsed_jd, max_candidates=15)
for log in trace:
    print(log)

# Stage 3: Seed ChromaDB
print("\n[STAGE 3] Seeding Vector DB")
seed_from_candidates(candidates)

print("\n" + "=" * 60)
print(f"DAY 1 COMPLETE — {len(candidates)} real candidates in vector DB")
print("=" * 60)