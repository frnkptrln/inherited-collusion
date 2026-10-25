from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,urllib.request
root=Path(__file__).resolve().parent
url='https://deepinfra.com/openai/gpt-oss-120b/api';name='deepinfra-model-api.html'
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'collusion-sprint-public-readonly/1.0'}),timeout=40) as response:data=response.read()
(root/name).write_bytes(data)
idx=json.loads((root/'retrieval-index.json').read_text());idx.append({'file':name,'url':url,'status':200,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'retrieved_at':datetime.now(timezone.utc).isoformat()});(root/'retrieval-index.json').write_text(json.dumps(idx,indent=2)+'\n')
sha=json.loads((root/'gpt-oss-mapping.json').read_text())['sha'];headers=[]
for filename in ('tokenizer.json','tokenizer_config.json','chat_template.jinja'):
 url=f'https://huggingface.co/openai/gpt-oss-120b/resolve/{sha}/{filename}'
 with urllib.request.urlopen(urllib.request.Request(url,method='HEAD',headers={'User-Agent':'collusion-sprint-public-readonly/1.0'}),timeout=40) as response:
  # Never store CDN signed redirect URLs. Only ordinary public source URL and content headers.
  headers.append({'url':url,'status':response.status,'etag':response.headers.get('etag'),'x_repo_commit':response.headers.get('x-repo-commit'),'content_length':response.headers.get('content-length')})
(root/'pinned-file-head-checks.json').write_text(json.dumps(headers,indent=2)+'\n');print('Saved API page and three public pinned HEAD metadata checks.')
