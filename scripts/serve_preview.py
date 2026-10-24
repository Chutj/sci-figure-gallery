"""Validate a public build, then serve a disposable same-origin local preview."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from urllib.parse import urlsplit

from validate_public_gallery import validate

ROOT=Path(__file__).resolve().parents[1]


def build(hugo,root=ROOT,base_url='http://127.0.0.1:1320/'):
    root=Path(root).resolve();validate(root)
    output=root/'.gallery-dev/previews'/uuid.uuid4().hex/'site'
    result=subprocess.run([hugo,'build','--environment','production','--minify','--noBuildLock','--baseURL',base_url,'--destination',str(output)],
        cwd=root,capture_output=True,text=True,encoding='utf-8')
    if result.returncode or result.stderr or 'WARN' in result.stdout:
        raise ValueError('Production preview build failed: '+result.stdout+result.stderr)
    validate(root,output)
    pattern=re.compile(r'(<script\b[^>]*\bid=["\']?gallery-data["\']?[^>]*>)(.*?)(</script>)',re.S)
    for path in (output/'index.html',output/'gallery/index.html'):
        html=path.read_text(encoding='utf-8')
        def localize(match):
            figures=json.loads(match[2])
            def local(url):
                parsed=urlsplit(url)
                if parsed.scheme!='https' or parsed.netloc!='chutj.github.io' or not parsed.path.startswith('/figures/approved/'):
                    raise ValueError('Only the exact reviewed site-hosted media can be previewed')
                return parsed.path
            for figure in figures:
                figure['image']=local(figure['image']);figure['thumbnail']=local(figure['thumbnail'])
                if 'legend' in figure: figure['legend']['image']=local(figure['legend']['image'])
                figure['srcset']=', '.join(local(part.strip().split()[0])+' '+part.strip().split()[1]
                    for part in figure['srcset'].split(',') if part.strip())
            tag=re.sub(r'data-mode=(?:"public"|\'public\'|public)', 'data-mode="candidate"',match[1])
            payload=json.dumps(figures,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
            return tag+payload+match[3]
        html,count=pattern.subn(localize,html)
        if count!=1:raise ValueError('Expected exactly one reviewed Gallery data element')
        path.write_text(html,encoding='utf-8')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hugo',default=shutil.which('hugo') or 'hugo')
    parser.add_argument('--port',type=int,default=1320);parser.add_argument('--build-only',action='store_true');args=parser.parse_args()
    output=build(args.hugo,base_url=f'http://127.0.0.1:{args.port}/');print('Validated local preview: '+str(output),flush=True)
    if not args.build_only:
        server=ThreadingHTTPServer(('127.0.0.1',args.port),functools.partial(SimpleHTTPRequestHandler,directory=str(output)))
        print(f'Preview: http://127.0.0.1:{args.port}/gallery/ (rerun after source changes)',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:server.server_close()
