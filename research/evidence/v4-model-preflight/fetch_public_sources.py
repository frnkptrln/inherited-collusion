from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parent
sources={
 'router-models.json':'https://router.huggingface.co/v1/models',
 'gpt-oss-mapping.json':'https://huggingface.co/api/models/openai/gpt-oss-120b?expand[]=inferenceProviderMapping&expand[]=sha',
 'gpt-oss-tokenizer.json':'https://huggingface.co/openai/gpt-oss-120b/resolve/main/tokenizer.json',
 'gpt-oss-tokenizer-config.json':'https://huggingface.co/openai/gpt-oss-120b/resolve/main/tokenizer_config.json',
 'gpt-oss-chat-template.jinja':'https://huggingface.co/openai/gpt-oss-120b/resolve/main/chat_template.jinja',
 'gpt-oss-readme.md':'https://huggingface.co/openai/gpt-oss-120b/raw/main/README.md',
 'deepinfra-model.html':'https://deepinfra.com/openai/gpt-oss-120b',
 'deepinfra-reasoning.md':'https://docs.deepinfra.com/chat/reasoning.md',
 'deepinfra-chat-schema.md':'https://docs.deepinfra.com/api-reference/chat-completions/openai-chat-completions.md',
}
index=[]
for name,url in sources.items():
 try:
  request=urllib.request.Request(url,headers={'User-Agent':'collusion-sprint-readonly-public-preflight/1.0'})
  with urllib.request.urlopen(request,timeout=45) as response:
   data=response.read();status=response.status
  (ROOT/name).write_bytes(data)
  row={'file':name,'url':url,'status':status,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat()}
 except urllib.error.HTTPError as error:
  row={'file':name,'url':url,'status':error.code,'retrieved_at':datetime.now(timezone.utc).isoformat()}
 index.append(row)
 (ROOT/'retrieval-index.json').write_text(json.dumps(index,indent=2)+'\n')
 print(json.dumps({'file':name,'status':row['status'],'bytes':row.get('bytes')}),flush=True)
