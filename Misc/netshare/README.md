# netshare

- **Category:** Misc
- **Author:** 
- **Points:** 
- **Solves:** 

## Description

Kubernetes on-demand 题目：每支队伍获得一个独立的临时 workload 集群，利用
EndpointSlice 数据陈旧与 Pod IP 复用完成提权。

## Architecture

- `kubernetes-on-demand-main/` — KOND controller：`docker compose` 启动，`nc` 监听
  :8888，每条连接创建一套 CAPI workload 集群，并自动应用 `challenge.yaml` / `user.yaml`。
- `ctf-challenge/` — 题目主体（`challenge.yaml`：命名空间、受害服务、陈旧
  EndpointSlice 控制器、各类策略；`user.yaml`：选手低权身份 `runtime-operator`）。
- `ret2shell-ext-controller-pod/` — ret.sh 实例 bridge pod 镜像源码
  （`app.py` nc 桥 + `pod.yaml` + `checker.rx`），已 build/push 为
  `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest`。

## Deployment

bridge 镜像已 build/push：`registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest`。
完整部署步骤见下文「部署(ret.sh 按需环境)」。

---

# Net Share

Net Share 是一道关于 EndpointSlice 数据陈旧与 Pod IP 复用的 Kubernetes CTF 题目。
线上通过 **ret.sh** 平台按需下发:每支队伍由 ret.sh 拉起一个 bridge pod,经
`nc` 与 KOND controller 交互,由 controller 为该队伍创建独立的 workload 集群、
按 team id 生成专属 flag,并把 kubeconfig 进行返回


## 部署(ret.sh 按需环境)

整体流程:

```text
选手点击「创建」
  → ret.sh 拉起 bridge pod(注入 RET2SHELL_TEAM_ID + CONTROLLER_HOST + CONTROLLER_PORT)
  → bridge pod 通过 nc 连接 controller,发送 team id
  → controller 为该队伍创建独立 workload 集群,
     用 team id 生成 sk-<uuid> flag 并注入 service assertion
  → controller 回传 runtime-operator 的 kubeconfig
  → bridge pod 在 :5000 网页上展示 kubeconfig
  → 选手用该 kubeconfig 在自己的集群里完成利用
停止实例 → bridge pod 退出 → nc 连接断开 → controller 自动销毁该集群
```

组件:

| 路径 | 作用 |
|---|---|
| `kubernetes-on-demand-main/` | KOND controller:`docker compose` 启动,`nc` 监听 :8888;每条连接创建一套 CAPI workload 集群,并自动把 `challenge.yaml` / `user.yaml` 应用进去。 |
| `ctf-challenge/challenge.yaml` | 题目主体:命名空间、受害服务 `profile-query`、陈旧 EndpointSlice 控制器、各类策略与平台 worker。 |
| `ctf-challenge/user.yaml` | 选手低权身份 `runtime-operator` 及其 RBAC。 |
| `ret2shell-ext-controller-pod/` | ret.sh 实例 bridge pod:`app.py`(nc 桥)、`pod.yaml`(实例清单)、`checker.rx`(flag 校验)。 |

### 部署步骤

1. 启动 controller:

```bash
cd kubernetes-on-demand-main
PUBLIC_HOST=<选手可达的 controller 主机 IP> \
FLAG_SALT=<与平台一致的盐> FLAG_CHAL_ID=<与平台一致的题目 id> \
docker compose up -d
```

controller 会监听 `nc` :8888,并为每条连接创建一套 workload 集群。

2. 对齐 flag 参数(controller 与 ret.sh `checker.rx` 必须一致,否则提交不通过):

   - controller `FLAG_SALT`  == `checker.rx` 的 `ENCRYPT_KEY`
   - controller `FLAG_CHAL_ID` == `checker.rx` 的 `HASH_KEY`

3. 构建并推送 bridge pod 镜像:

```bash
cd ret2shell-ext-controller-pod
docker build -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest .
docker push registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest
```

4. 在 ret.sh 上配置题目:

   - `ret2shell-ext-controller-pod/checker.rx`:将 `CONTROLLER_HOST` / `CONTROLLER_PORT`
     指向第 1 步的 controller;`ENCRYPT_KEY` / `HASH_KEY` 按第 2 步对齐;按平台约定
     处理 `sk-` 前缀的解析(flag 形如 `sk-<uuid>`,不带花括号)
   - `ret2shell-ext-controller-pod/pod.yaml`:把 `image` 改成第 3 步的镜像
   - 将 `checker.rx` 设为该题的 flag checker,`pod.yaml` 设为实例清单


### 环境要求

workload 集群由 controller 按模板(`kubernetes-on-demand-main/resources/`)自动创建,
已具备以下使漏洞成立的特性:

- Kubernetes v1.28(由 CAPI 创建,默认启用 `ValidatingAdmissionPolicy`)。
- Calico CNI,`blockSize: 28` 的小分配块,使旧后端 IP 能被目标 Pod 重新占用。
- 节点预置 `python:3.11-alpine` 镜像(目标 Pod 使用 `imagePullPolicy: Never`)

### 本地快速验证(不经 ret.sh)

可直接用一条 `nc` 模拟 bridge pod 的行为:

```bash
printf '62\n' | nc <controller 主机> 8888   # 保持连接打开
```

输出中 `-----BEGIN KUBECONFIG-----` 与 `-----END KUBECONFIG-----` 之间即为 kubeconfig;
保存后即可 `kubectl --kubeconfig <文件> get ns`, 关闭该连接会销毁对应集群

### 验证可用权限

拿到 kubeconfig 后:

```bash
export KUBECONFIG="$PWD/runtime-operator.kubeconfig"
kubectl get pods -n tenant-runtime
kubectl get pods,svc,endpoints,endpointslices -n customer-platform -o wide
```


