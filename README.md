Assessment Report Generator Rebuild Command
```cmd
cd "/var/www/credit-report-analyzer/Automations/Assessment Report Generator"
git pull
docker stop credit-report-analyzer
docker rm credit-report-analyzer
docker build -t credit-report-analyzer .
docker run -d \
  --name credit-report-analyzer \
  --env-file .env \
  -p 8001:8001 \
  --restart unless-stopped \
  -v "/var/www/credit-report-analyzer/Automations/Assessment Report Generator/credentials:/app/credentials" \
  credit-report-analyzer
```
