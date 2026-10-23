import os,subprocess,re
from pathlib import Path
env=os.environ.copy()
for line in Path("/etc/hunter-ksa1-backend/db-connections.env").read_text().splitlines():
    name,sep,value=line.partition("=")
    if sep and name in ("DATABASE_URL","MIGRATION_DATABASE_URL"):
        env[name]=value
env["PYTHONPATH"]="/opt/hunter_ksa1-bot/apps/api"
env["ENVIRONMENT"]="test"
p=subprocess.run(["/opt/hunter_ksa1-bot/.venv-qa/bin/python","-m","alembic",
 "-c","apps/api/alembic.ini","upgrade","head"],env=env,cwd="/opt/hunter_ksa1-bot",
 capture_output=True,text=True)
print("EXIT_CODE",p.returncode)
for line in (p.stderr+"\n"+p.stdout).splitlines():
    if any(word in line for word in ("Error", "ERROR", "Exception", "Undefined", "Duplicate",
      "Denied","Programming","migration","Running upgrade","CREATE POLICY","insufficient","ALTER TABLE")):
        line=re.sub(r"(postgresql[^\s]*://)[^@\s]+@",r"\1[REDACTED]@",line)
        print(line[:300])
