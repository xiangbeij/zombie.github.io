# 閮ㄧ讲鎸囧崡

鏈枃妗ｈ缁嗚鏄庡浣曞湪 Linux 鏈嶅姟鍣ㄤ笂閮ㄧ讲 ORION 瀹夊叏鐩戞祴骞冲彴銆?
## 鐜瑕佹眰

- **鎿嶄綔绯荤粺:** Rocky Linux 9.7 / CentOS 7+ / Ubuntu 20.04+
- **CPU:** 2 鏍?
- **鍐呭瓨:** 4GB+
- **Go:** 1.21+
- **Python:** 3.8+
- **Node.js:** 16+ (鐢ㄤ簬鏋勫缓鍓嶇)

## 涓€銆佸畨瑁呯郴缁熶緷璧?
```bash
# Rocky Linux 9
sudo dnf install -y golang python3 python3-pip git

# 瀹夎 Node.js 16
curl -fsSL https://rpm.nodesource.com/setup_16.x | sudo bash -
sudo dnf install -y nodejs

# Ubuntu
sudo apt update
sudo apt install -y golang python3-pip nodejs npm git
```

## 浜屻€侀儴缃插悗绔湇鍔?
### 2.1 鍒涘缓鐩綍

```bash
sudo mkdir -p /opt/Orion
sudo chown $USER:$USER /opt/Orion
```

### 2.2 涓婁紶浠ｇ爜

```bash
# 鏂规硶1: Git 鍏嬮殕
git clone https://github.com/xiangbeij/zombie.github.io.git /tmp/Orion
cp -r /tmp/Orion/Orion/* /opt/Orion/

# 鏂规硶2: SCP 涓婁紶
scp -r ./Orion root@your-server:/opt/
```

### 2.3 瀹夎 Python 渚濊禆

```bash
cd /opt/Orion
pip3 install -r requirements.txt

# 鍏抽敭渚濊禆:
# - Flask>=2.0
# - Requests>=2.28
# - APScheduler>=3.10
# - WeasyPrint>=66.0  (PDF鎶ュ憡)
```

### 2.4 缂栬瘧 Go API

```bash
cd /opt/Orion/Orion-server/go

# 缂栬瘧涓籄PI (浣跨敤 CGO 鑾峰緱瀹屾暣 sqlite3 鏀寔)
CGO_ENABLED=1 go build -o orion-api-new2-linux .

# 缂栬瘧璧勪骇鎵弿鍣?CGO_ENABLED=1 go build -o Orion-assets-linux .
```

### 2.5 鍒濆鍖栨暟鎹簱

```bash
cd /opt/Orion
python3 check_init.py      # 妫€鏌ュ垵濮嬪寲鐘舵€?python3 check_db.py        # 楠岃瘉鏁版嵁搴?```

### 2.6 鍚姩鏈嶅姟

```bash
# 鍚姩 Flask API (绔彛 5188)
cd /opt/Orion/Orion-server
nohup python3 app_batch.py > /var/log/libra_api.log 2>&1 &
echo $! > /tmp/libra_api.pid

# 鍚姩 Go API (绔彛 5188, 鏇挎崲 Flask)
nohup ./go/orion-api-new2-linux > /var/log/libra_go.log 2>&1 &
echo $! > /tmp/libra_go.pid

# 鍚姩璧勪骇 Flask API (绔彛 5187)
nohup python3 orion_assets.py > /var/log/orion_assets.log 2>&1 &
echo $! > /tmp/orion_assets.pid

# 鍚姩闈欐€佹枃浠舵湇鍔?(绔彛 5189)
nohup python3 serve.py > /var/log/libra_web.log 2>&1 &
echo $! > /tmp/libra_web.pid
```

### 2.7 楠岃瘉鏈嶅姟

```bash
# 妫€鏌ョ鍙?ss -tlnp | grep -E '5187|5188|5189'

# 娴嬭瘯 API
curl http://localhost:5188/api/health
curl http://localhost:5187/health
```

## 涓夈€侀儴缃插墠绔?
### 3.1 鏋勫缓鍓嶇

```bash
cd /opt/Orion/Orion-web
npm install
npm run build
```

### 3.2 閰嶇疆 Nginx (鍙€夛紝鐢ㄤ簬鐢熶骇鐜)

```nginx
server {
    listen 80;
    server_name your-domain.edu.cn;

    # 鍓嶇闈欐€佹枃浠?    location / {
        root /opt/Orion/Orion-web/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 鍙嶅悜浠ｇ悊
    location /api {
        proxy_pass http://127.0.0.1:5188;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 鍥涖€佹湇鍔＄鐞?
### 4.1 鍚姩鎵€鏈夋湇鍔?
```bash
# 浣跨敤椤圭洰鑷甫鑴氭湰
python3 /opt/Orion/start_orion.py

# 鎴栨墜鍔?bash /opt/Orion/deploy.sh
```

### 4.2 閲嶅惎鏈嶅姟

```bash
python3 /opt/Orion/restart_orion.py
```

### 4.3 鏌ョ湅鐘舵€?
```bash
python3 /opt/Orion/check_status.py
```

## 浜斻€丏ocker 閮ㄧ讲锛堝彲閫夛級

```bash
cd /opt/Orion
python3 build_docker.py    # 鏋勫缓闀滃儚
python3 deploy_docker2.py   # 閮ㄧ讲瀹瑰櫒
```

## 鍏€佸父瑙侀棶棰?
### Q: API 杩斿洖绌烘暟鎹?A: 妫€鏌?SQLite 鏁版嵁搴撴潈闄愶紝纭繚 Go 浜岃繘鍒朵娇鐢?`CGO_ENABLED=1` 缂栬瘧銆?
### Q: 鍓嶇鏃犳硶璁块棶
A: 纭 5189 绔彛宸插紑鏀撅紝闈欐€佹枃浠舵湇鍔℃甯歌繍琛屻€?
### Q: 鎵弿浠诲姟鍫嗙Н
A: Worker Pool 榛樿20骞跺彂锛岄槦鍒楀閲?000銆傛鏌ヤ换鍔＄Н鍘嬫儏鍐碉細
```bash
curl http://localhost:5188/api/stats
```

### Q: PDF 鎶ュ憡鏃犳硶鐢熸垚
A: 瀹夎 WeasyPrint 渚濊禆锛?```bash
pip3 install WeasyPrint>=66.0
# 杩橀渶瑕佺郴缁熺骇渚濊禆锛堝弬鑰?WeasyPrint 鏂囨。锛?```

## 涓冦€佸畨鍏ㄩ厤缃?
### 7.1 淇敼榛樿瀵嗙爜

棣栨閮ㄧ讲鍚庤绔嬪嵆淇敼 `admin` 璐︽埛瀵嗙爜銆?
### 7.2 闃茬伀澧欓厤缃?
```bash
# 浠呭紑鏀惧繀瑕佺鍙?firewall-cmd --permanent --add-port=5188/tcp  # API
firewall-cmd --permanent --add-port=5187/tcp  # 璧勪骇API
firewall-cmd --permanent --add-port=5189/tcp  # Web UI
firewall-cmd --reload
```

### 7.3 绂佹绔彛21/80

> 鈿狅笍 娉ㄦ剰锛氱郴缁熷凡閰嶇疆璺宠繃 FTP(21) 鍜?SCOW HPC 鐨?Web(80)锛岃鍕垮湪鐢熶骇鐜寮€鏀捐繖浜涚鍙ｃ€?
---

*閮ㄧ讲鏂囨。鏈€鍚庢洿鏂? 2026-04-20*
