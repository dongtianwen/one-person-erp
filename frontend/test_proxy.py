import asyncio
import httpx

async def test_proxy():
    async with httpx.AsyncClient(base_url='http://localhost:5176', timeout=10.0) as client:
        resp = await client.post('/api/v1/auth/login', data={"username": "admin", "password": "admin123"})
        print('Status:', resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            print('Token received:', data.get('access_token', 'NO TOKEN')[:50] if data.get('access_token') else 'NO TOKEN')

            token = data.get('access_token')
            if token:
                headers = {'Authorization': f'Bearer {token}'}
                ds_resp = await client.get('/api/v1/datasets', headers=headers)
                print('Datasets Status:', ds_resp.status_code)
                if ds_resp.status_code == 200:
                    print('Datasets Data:', ds_resp.json())
                else:
                    print('Datasets Error:', ds_resp.text)
        else:
            print('Login Error:', resp.text)

asyncio.run(test_proxy())