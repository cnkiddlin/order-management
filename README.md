# order-management

订单查询系统，支持按订单编号查询订单详情，并给指定处理者发送催办通知。

## 本地运行

先启动催办通知服务（默认监听 `8081`）：

```bash
cd ../order-notification
pip install -r requirements.txt
python app.py
```

再启动本服务（默认监听 `8080`）：

```bash
pip install -r requirements.txt
python app.py
```

浏览器访问 `http://127.0.0.1:8080`。催办请求默认转发到
`http://localhost:8081`，可通过环境变量 `NOTIFICATION_SERVICE_URL` 修改。

两个服务放在容器里运行时，不能把催办地址写成容器内的 `localhost`。最简单的方式是把两个容器放进同一个网络，用容器名访问：

```bash
podman network create order-net
podman run -d --network order-net --name order-notification order-notification:v1
podman run -d --network order-net -p 8080:8080 \
  -e NOTIFICATION_SERVICE_URL=http://order-notification:8081 \
  --name order-management order-management:v1
```

如果催办服务已经单独映射到宿主机 `8081`，也可以让管理端容器通过
`http://host.containers.internal:8081` 访问宿主机的映射端口。

## 接口

- `GET /api/order/<order_id>` 查询订单
- `GET /api/orders/suggest` 获取订单建议列表
- `GET /api/handlers` 获取处理者列表
- `POST /api/reminders` 发送催办，入参为 `order_id` 和 `handler`

## 构建与部署

两个服务在 OpenShift 上分别使用独立的 Deployment：

- `order-management`：提供 UI 和查询接口，通过 Route 对外访问
- `order-notification`：催办通知服务，只创建 ClusterIP Service，不对外暴露

部署清单见两个项目各自的 `openshift/deployment.yaml`。先部署
`order-notification`，再部署 `order-management`。`order-management`
通过环境变量调用催办服务，同一项目（namespace）内使用：

```yaml
env:
  - name: NOTIFICATION_SERVICE_URL
    value: http://order-notification:8081
```

跨项目部署时使用完整服务域名，例如
`http://order-notification.<namespace>.svc.cluster.local:8081`。
