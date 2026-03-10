from aiohttp import web

routes = web.RouteTableDef()

@routes.get('/')
async def health(request):
    return web.json_response({'status': 'ok', 'bot': 'running'})

@routes.get('/health')
async def healthcheck(request):
    return web.json_response({'status': 'healthy'})

async def web_server():
    app = web.Application()
    app.add_routes(routes)
    return app
