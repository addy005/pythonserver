import os
import sys
import urllib.parse
import json
import aiohttp
import asyncio
from aiohttp import web

VIDEO_FOLDER = 'video'
PORT = 8080
BASE_URL = f'http://212.47.229.194:{PORT}'  # Updated with your server IP

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

async def get_video_links():
    video_files = [f for f in os.listdir(VIDEO_FOLDER) if os.path.isfile(os.path.join(VIDEO_FOLDER, f))]
    direct_links = [f'{BASE_URL}/video/{urllib.parse.quote(video)}' for video in video_files]
    
    short_urls = await asyncio.gather(*[shorten_url(url) for url in direct_links])
    
    return {'direct': direct_links, 'short': short_urls}

async def handle_root(request):
    content = generate_html()
    return web.Response(text=content, content_type='text/html')

async def handle_video(request):
    filename = request.match_info['filename']
    file_path = os.path.join(VIDEO_FOLDER, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return web.FileResponse(file_path)
    else:
        raise web.HTTPNotFound()

async def handle_get_links(request):
    links = await get_video_links()
    return web.json_response(links)

def generate_html():
    video_files = [f for f in os.listdir(VIDEO_FOLDER) if os.path.isfile(os.path.join(VIDEO_FOLDER, f))]
    video_list = ''.join([
        f'<li><span class="number">{i+1}.</span> <a href="/video/{urllib.parse.quote(video)}">{video}</a> '
        f'({get_file_size(os.path.join(VIDEO_FOLDER, video))})</li>'
        for i, video in enumerate(video_files)
    ])

    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Video Server</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #121212;
                color: #ffffff;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: #1e1e1e;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            h1 {{
                text-align: center;
                color: #4CAF50;
                margin-bottom: 30px;
            }}
            ul {{
                list-style-type: none;
                padding: 0;
            }}
            li {{
                margin-bottom: 15px;
                padding: 10px;
                background-color: #2c2c2c;
                border-radius: 4px;
                transition: background-color 0.3s;
            }}
            li:hover {{
                background-color: #363636;
            }}
            .number {{
                color: #4CAF50;
                font-weight: bold;
                margin-right: 10px;
            }}
            a {{
                color: #4CAF50;
                text-decoration: none;
                transition: color 0.3s;
            }}
            a:hover {{
                color: #45a049;
                text-decoration: underline;
            }}
            .button-container {{
                display: flex;
                flex-wrap: wrap;
                justify-content: space-between;
                margin-top: 30px;
            }}
            .button {{
                background-color: #4CAF50;
                color: white;
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
                background-color: #45a049;
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
                border-top: 5px solid #4CAF50;
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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Video Server</h1>
            <ul>
                {video_list}
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
        </div>
        <script>
            function showProgress() {{
                document.getElementById('progress').style.display = 'block';
            }}

            function hideProgress() {{
                document.getElementById('progress').style.display = 'none';
            }}

            function copyLinks(type) {{
                showProgress();
                fetch('/get_links')
                    .then(response => response.json())
                    .then(data => {{
                        const links = data[type].join('\\n');
                        navigator.clipboard.writeText(links)
                            .then(() => {{
                                hideProgress();
                                alert('Links copied to clipboard!');
                            }})
                            .catch(err => {{
                                console.error('Error copying links: ', err);
                                fallbackCopyTextToClipboard(links);
                            }});
                    }});
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
                hideProgress();
            }}

            function downloadLinks(type) {{
                showProgress();
                fetch('/get_links')
                    .then(response => response.json())
                    .then(data => {{
                        const links = data[type].join('\\n');
                        const blob = new Blob([links], {{ type: 'text/plain' }});
                        const a = document.createElement('a');
                        a.href = URL.createObjectURL(blob);
                        a.download = `${{type}}_links.txt`;
                        a.click();
                        hideProgress();
                    }});
            }}
        </script>
    </body>
    </html>
    '''

async def run_server(port=8080):
    app = web.Application()
    app.router.add_get('/', handle_root)
    app.router.add_get('/video/{filename}', handle_video)
    app.router.add_get('/get_links', handle_get_links)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    print(f'Server running on http://212.47.229.194:{port}')
    print(f'Serving files from: {os.path.abspath(VIDEO_FOLDER)}')
    
    await site.start()
    
    # The server will run until interrupted
    while True:
        await asyncio.sleep(3600)  # Sleep for an hour (or any long duration)

if __name__ == '__main__':
    if not os.path.exists(VIDEO_FOLDER):
        print(f"Error: The '{VIDEO_FOLDER}' folder does not exist.")
        print(f"Please create a '{VIDEO_FOLDER}' folder in the same directory as this script and place your video files in it.")
        sys.exit(1)
    
    asyncio.run(run_server(PORT))
