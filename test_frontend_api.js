// 测试前端 API 调用
const axios = require('axios');

async function test() {
    // 登录
    const loginRes = await axios.post('http://localhost:8001/api/v1/auth/login', null, {
        params: {
            username: 'admin',
            password: 'admin123'
        }
    });
    console.log('Login response:', loginRes.data);
    
    const token = loginRes.data.access_token;
    console.log('Token:', token);
    
    // 获取变更单
    const changeOrdersRes = await axios.get('http://localhost:8001/api/v1/projects/1/change-orders', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    console.log('Change Orders response:', JSON.stringify(changeOrdersRes.data, null, 2));
}

test().catch(console.error);
