# curl 'https://portal-api.coinmarketcap.com/v1/accounts/my/plan/stats' \
#   -H 'accept: application/json' \
#   -H 'accept-language: zh-CN,zh;q=0.9' \
#   -H 'authorization: Basic Og==' \
#   -H 'cache-control: no-cache' \
#   -H 'content-type: application/json' \
#   -H 'cookie: OptanonAlertBoxClosed=2024-10-08T04:33:37.283Z; OTGPPConsent=DBABLA~BVQqAAAACgA.QA; _cc_id=7c7d5c655fc2e4beed278a23de47ce51; se_gd=RZVClAF4QFJClERMNEg8gZZAQDQQMBSVVcGdYUkRVFTUQUlNWUNd1; se_gsd=fywmATdlIigiJ1YyIQgiMDkzEAJRAQUVUVlFUVRSUFFVAlNT1; _ga=GA1.2.1247553371.1730720239; bnc-uuid=74a623de-cb4c-4ae1-910e-0275b2dbb9f8; _gcl_au=1.1.114454409.1740750479; cto_bundle=ArEpO19sTzl5Y1QlMkZGS3RwTFNNQktSQ2w5TXI4JTJCb21hWjJaRno3dVMxdTlmUUglMkZRbzNjOHpjJTJCdXVrVHYzc0tHbVglMkZzbjU0QkhDSnRwRUx5Nno0VTFYSmF6cjFyJTJGQkFtRVBVb09vaUdUM3hCT2pYR3NybjIwdTIlMkIlMkY5RzJvJTJCWG5zcjdOcDlKU0Z4OGFzZTlLYXc1UnUlMkY0WW9wQSUzRCUzRA; cto_bidid=QVGTXF9vZkRoVTJYaiUyRjJzZUxiRGMlMkIlMkJQem1nbVZWJTJCUFFuWUtuTUQxa3hRQkUxMWl4WmtPZEhLR3lZaDB2aGlhQVFQcTNJcWN3ZWZRT2Y1emJxWkhkUUxibGw1QVpiVEN1Z21vd2dCREpCTU5DNzZwS1dyRklpSXZOSG01WEVXVzkyZmU0; __gads=ID=62404a4a9711d52b:T=1728362022:RT=1744856637:S=ALNI_MbVA17yurTEx-gE6pINJIuQ5wvyMw; __gpi=UID=00000f265bf3e46e:T=1728362022:RT=1744856637:S=ALNI_Maqa7UHQF1yvscg4B-eCZciSKpDTw; __eoi=ID=ef650bc7fb1d37a1:T=1744856637:RT=1744856637:S=AA-AfjaLd8_Y2Rs_k20cmTYhpKH5; se_sd=RYDB1BV4QREDlQawFWgcgZZHVFVcFEXUFsBNcV05lZXUwCVNWVBT1; c=831np5wAndepsQEICLPXT_RgYFu4hAm5qLSmZBlXRgo; OptanonConsent=isGpcEnabled=0&datestamp=Mon+May+19+2025+10%3A01%3A16+GMT%2B0800+(China+Standard+Time)&version=202409.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=ba6dc199-cb2b-4b4a-b048-6b73fda3276c&interactionCount=2&landingPath=NotLandingPage&groups=C0003%3A1%2CC0001%3A1%2CC0004%3A1%2CC0002%3A1&AwaitingReconsent=false&isAnonUser=1&intType=1&GPPCookiesCount=1&geolocation=SG%3B; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%226728b113a214795bc446a39b%22%2C%22first_id%22%3A%2218bb70323c671e-0dd70dd60023f58-26031151-2073600-18bb70323c712bd%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E8%87%AA%E7%84%B6%E6%90%9C%E7%B4%A2%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMThiYjcwMzIzYzY3MWUtMGRkNzBkZDYwMDIzZjU4LTI2MDMxMTUxLTIwNzM2MDAtMThiYjcwMzIzYzcxMmJkIiwiJGlkZW50aXR5X2xvZ2luX2lkIjoiNjcyOGIxMTNhMjE0Nzk1YmM0NDZhMzliIn0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%226728b113a214795bc446a39b%22%7D%2C%22%24device_id%22%3A%2218bb70323c671e-0dd70dd60023f58-26031151-2073600-18bb70323c712bd%22%7D; BNC_FV_KEY=335fe043b6fc960292e0a5f451ee21212b6b4492; BNC_FV_KEY_EXPIRE=1747812255985; s=Fe26.2**8c7d9aa5f2d239e95ca0fc63ba7987aef1c0b00655871929308030bdb706eae9*t1ezumSKkqxxzxhXjgvVkw*v8OD8LUCBB6l4WU7G_f3KrjtyjOf8y1tcig6g1DVtEoTsfxsmnGFU1H6qOn83WwpL7zZ4C4drKjasvbdPvLeFk5031u7NZ0EuhOEwXcAYU3akSpJE3c-CdJmSzb7DCSanaHIe5nxQn5JY75SKJggiqGvRAM1xvqWLVFbp68m4GkbcR48_UiqTWr-vJc3DtASY5YQhgDdp4Mub-wsHNDnQC334lh8pDvIy91fVfXissbjgFsAE1XTWAAUQmqvi2SidQnmhk9DGh3vRt5WiE57OstjUaS-nOeIEsMD-fmlaqRP4764fXW86R5cC1warWXpXeGdmAHjrfy-Ts-jHkfM948gJAqnhUBByT0Rh7vT2mt-4lwxURWXmJ4JX0_a1QJiLUWqNUzc9nLqxhdppycr7pozMxMU2zg7mgoUaIKncNAqiCYHQQREXXk_AI4Ya79NQXiirf0JIQLIjpWNhv3Z87t4D6WSLoo7RsNh2Q5e3oaWvPI43IRlpKJ5MmiRg0-adsD7Hx3T0FdjWzjNKQFfcaWVaATM4wk5gUyGNk3VcBs0BFYasBT57TDAN2yTTRvykyXZdXfdBPKJz3IByF3HbzsKZyb_RrcUqz3IGWSp9H-piYDKFnvqYNNS8k-KQGLy37XbDv0XhTdvtFIsWnmUcrQ11ibUzZiqW0n6fV2MMBbYiYvYvvWPjgosEM3Hj1qmHYXPNxHllZBAD-42czkLK5bmE2TdalDPK4M4EgY9vJgcg8u666e5Y8RFp2kohA-vQVOdBWT_FCp4w8c-rz_tGxo6RuDcWamlzCAP3kOlqecngLVWqpyDaRKDbiATaxLWFc52Cf1vGTi8VBO_QXRk2rFkS-e_HMp4pvXgIKTvvydI3yfn0CSt3sRF1ZjkdjD0WTbJOQzfAgu9lua8_aGFTDilzLugm3WaaJZVDVtGi1onInJQ7KeAIlZDtiNE1Tl3KHYcc0bhE_O2tkVcJFzk7G9dX41kLEKN_IwllRZkqXVJQWh8jOKt686JmU7bqoSv**37b31f9840d6b56398711cc07df3a79bc0d9f923e2507e70d2025635f49bea59*ocohiXjOPNuyf_BWp0i6KPlvlcIVTqX6bW4iZi2itEw' \
#   -H 'origin: https://pro.coinmarketcap.com' \
#   -H 'pragma: no-cache' \
#   -H 'priority: u=1, i' \
#   -H 'referer: https://pro.coinmarketcap.com/' \
#   -H 'sec-ch-ua: "Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"' \
#   -H 'sec-ch-ua-mobile: ?0' \
#   -H 'sec-ch-ua-platform: "Windows"' \
#   -H 'sec-fetch-dest: empty' \
#   -H 'sec-fetch-mode: cors' \
#   -H 'sec-fetch-site: same-site' \
#   -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36' \
#   -H 'x-requested-with: xhr'

import requests

url = 'https://portal-api.coinmarketcap.com/v1/accounts/my/plan/stats'


def start():
    headers = {
        'accept': 'application/json',
        'accept-language': 'zh-CN,zh;q=0.9',
        'authorization': 'Basic Og==',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://pro.coinmarketcap.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://pro.coinmarketcap.com/',
        'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'x-requested-with': 'xhr',
    }
    response = requests.get(url, headers=headers, proxies={'https': 'http://127.0.0.1:10811'})
    print(response.json())

if __name__ == '__main__':
    start()
