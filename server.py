import os
import sys
import urllib.parse
import json
import aiohttp
import asyncio
from aiohttp import web
from collections import defaultdict
import socket

# Get the IP address dynamically
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

IP = get_ip()
PORT = 8080
BASE_URL = f'http://{IP}:{PORT}'

def get_file_size(file_path):
    size_bytes = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0

async def shorten_url(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post('http://tinyurl.com/api-create.php', data={'url': url}, timeout=5) as response:
                return await response.text()
        except asyncio.TimeoutError:
            return url

async def get_file_links(directory, request):
    items = [f for f in os.listdir(directory) if not f.startswith('.')]
    links = []
    for item in items:
        full_path = os.path.join(directory, item)
        relative_path = os.path.relpath(full_path, start=request.app['root_directory'])
        url = f'{BASE_URL}/browse/{urllib.parse.quote(relative_path)}'
        links.append(url)
    
    short_urls = await asyncio.gather(*[shorten_url(url) for url in links])
    
    return {'direct': links, 'short': short_urls}

async def handle_root(request):
    return await handle_browse(request)

async def handle_browse(request):
    path = request.match_info.get('path', '')
    directory = os.path.join(request.app['root_directory'], path)
    
    if not os.path.exists(directory):
        raise web.HTTPNotFound()
    
    if os.path.isfile(directory):
        return web.FileResponse(directory)
    
    content = generate_html(directory, path, request)
    return web.Response(text=content, content_type='text/html')

async def handle_get_links(request):
    path = request.query.get('path', '')
    directory = os.path.join(request.app['root_directory'], path)
    links = await get_file_links(directory, request)
    return web.json_response(links)

def generate_html(directory, current_path, request):
    items = [f for f in os.listdir(directory) if not f.startswith('.')]
    folders = [f for f in items if os.path.isdir(os.path.join(directory, f))]
    files = [f for f in items if os.path.isfile(os.path.join(directory, f))]
    
    folders.sort()
    files.sort()
    
    item_list = []
    for i, folder in enumerate(folders):
        full_path = os.path.join(directory, folder)
        relative_path = os.path.relpath(full_path, start=request.app['root_directory'])
        item_list.append(f'''
        <li>
            <span class="number">{i+1}.</span>
            <a href="/browse/{urllib.parse.quote(relative_path)}">{folder}/</a>
        </li>
        ''')
    
    for i, file in enumerate(files):
        full_path = os.path.join(directory, file)
        relative_path = os.path.relpath(full_path, start=request.app['root_directory'])
        item_list.append(f'''
        <li>
            <span class="number">{i+len(folders)+1}.</span>
            <a href="/browse/{urllib.parse.quote(relative_path)}">{file}</a>
            ({get_file_size(full_path)})
            <a href="/browse/{urllib.parse.quote(relative_path)}" download class="download-icon" title="Download">↓</a>
        </li>
        ''')
    
    item_list = ''.join(item_list)
    
    # Count files by extension
    extension_counts = defaultdict(int)
    for file in files:
        _, ext = os.path.splitext(file)
        extension_counts[ext.lower()] += 1
    
    extension_summary = ''.join([
        f'<li>{ext}: {count}</li>' for ext, count in extension_counts.items()
    ])

    parent_path = os.path.dirname(current_path)
    parent_link = f'<a href="/browse/{urllib.parse.quote(parent_path)}">Parent Directory</a>' if current_path else ''

    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Advanced File Server</title>
        <style>
            :root {{
                --bg-color: #121212;
                --card-bg-color: #1e1e1e;
                --text-color: #ffffff;
                --accent-color: #4CAF50;
                --hover-color: #45a049;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-color);
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: var(--card-bg-color);
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            h1, h2 {{
                text-align: center;
                color: var(--accent-color);
                margin-bottom: 30px;
            }}
            ul {{
                list-style-type: none;
                padding: 0;
            }}
            li {{
                margin-bottom: 15px;
                padding: 10px;
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                transition: background-color 0.3s, transform 0.2s;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            li:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                transform: translateY(-2px);
            }}
            .number {{
                color: var(--accent-color);
                font-weight: bold;
                margin-right: 10px;
            }}
            a {{
                color: var(--accent-color);
                text-decoration: none;
                transition: color 0.3s;
            }}
            a:hover {{
                color: var(--hover-color);
                text-decoration: underline;
            }}
            .download-icon {{
                font-size: 1em;
                text-decoration: none;
                opacity: 0.7;
                transition: opacity 0.3s;
            }}
            .download-icon:hover {{
                opacity: 1;
            }}
            .button-container {{
                display: flex;
                flex-wrap: wrap;
                justify-content: space-between;
                margin-top: 30px;
            }}
            .button {{
                background-color: var(--accent-color);
                color: var(--text-color);
                border: none;
                padding: 12px 20px;
                margin: 5px;
                cursor: pointer;
                transition: background-color 0.3s, transform 0.1s;
                border-radius: 4px;
                font-size: 14px;
                flex: 1;
                text-align: center;
            }}
            .button:hover {{
                background-color: var(--hover-color);
                transform: translateY(-2px);
            }}
            .button:active {{
                transform: translateY(0);
            }}
            #progress {{
                display: none;
                text-align: center;
                margin-top: 20px;
            }}
            .loader {{
                border: 5px solid #f3f3f3;
                border-top: 5px solid var(--accent-color);
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 10px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .summary {{
                margin-top: 30px;
                background-color: rgba(255, 255, 255, 0.05);
                padding: 15px;
                border-radius: 4px;
            }}
            #server-url, #current-path, #parent-link {{
                text-align: center;
                margin-top: 20px;
                font-size: 1.2em;
                background-color: rgba(255, 255, 255, 0.05);
                padding: 10px;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Advanced File Server</h1>
            <div id="server-url">Server URL: <a href="{BASE_URL}">{BASE_URL}</a></div>
            <div id="current-path">Current Path: {current_path}</div>
            <div id="parent-link">{parent_link}</div>
            <ul>
                {item_list}
            </ul>
            <div class="button-container">
                <button class="button" onclick="copyLinks('direct')">Copy Direct Links</button>
                <button class="button" onclick="downloadLinks('direct')">Download Direct Links</button>
                <button class="button" onclick="copyLinks('short')">Copy Short Links</button>
                <button class="button" onclick="downloadLinks('short')">Download Short Links</button>
            </div>
            <div id="progress">
                <div class="loader"></div>
                <p>Processing links... Please wait.</p>
            </div>
            <div class="summary">
                <h2>File Summary</h2>
                <ul>
                    {extension_summary}
                    <li>Total files: {len(files)}</li>
                    <li>Total folders: {len(folders)}</li>
                </ul>
            </div>
        </div>
        <script>
            function showProgress() {{
                document.getElementById('progress').style.display = 'block';
            }}

            function hideProgress() {{
                document.getElementById('progress').style.display = 'none';
            }}

            async function copyLinks(type) {{
                showProgress();
                try {{
                    const response = await fetch('/get_links?path={urllib.parse.quote(current_path)}');
                    const data = await response.json();
                    const links = data[type].join('\\n');
                    await navigator.clipboard.writeText(links);
                    alert('Links copied to clipboard!');
                }} catch (err) {{
                    console.error('Error copying links: ', err);
                    fallbackCopyTextToClipboard(links);
                }} finally {{
                    hideProgress();
                }}
            }}

            function fallbackCopyTextToClipboard(text) {{
                const textArea = document.createElement("textarea");
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {{
                    const successful = document.execCommand('copy');
                    const msg = successful ? 'Links copied to clipboard!' : 'Unable to copy links';
                    alert(msg);
                }} catch (err) {{
                    console.error('Fallback: Oops, unable to copy', err);
                    alert('Failed to copy links. Please check the console for details.');
                }}
                document.body.removeChild(textArea);
            }}

            async function downloadLinks(type) {{
                showProgress();
                try {{
                    const response = await fetch('/get_links?path={urllib.parse.quote(current_path)}');
                    const data = await response.json();
                    const links = data[type].join('\\n');
                    const blob = new Blob([links], {{ type: 'text/plain' }});
                    const a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = `${{type}}_links.txt`;
                    a.click();
                }} catch (err) {{
                    console.error('Error downloading links: ', err);
                    alert('Failed to download links. Please check the console for details.');
                }} finally {{
                    hideProgress();
                }}
            }}
        </script>
    </body>
    </html>
    '''

async def run_server(directory, port=8080):
    app = web.Application()
    app['root_directory'] = os.path.abspath(directory)
    app.router.add_get('/', handle_root)
    app.router.add_get('/browse/{path:.*}', handle_browse)
    app.router.add_get('/get_links', handle_get_links)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    print(f'Server running on {BASE_URL}')
    print(f'Serving files from: {os.path.abspath(directory)}')
    
    await site.start()
    
    # The server will run until interrupted
    while True:
        await asyncio.sleep(3600)  # Sleep for an hour (or any long duration)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = '.'

    if not os.path.exists(directory):
        print(f"Error: The '{directory}' directory does not exist.")
        print(f"Please provide a valid directory path.")
        sys.exit(1)
    
    asyncio.run(run_server(directory, PORT))
