# Docker 构建和推送脚本
# 使用方法：
#   1. 修改 DOCKER_USERNAME 为你的 Docker Hub 用户名
#   2. 运行: docker-build-push.ps1
$DOCKER_USERNAME = "你的DockerHub用户名"
$IMAGE_NAME = "textnow-cs"

Write-Host "📦 构建 Docker 镜像..." -ForegroundColor Green
docker build -t ${DOCKER_USERNAME}/${IMAGE_NAME}:latest .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 构建失败" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 构建成功，正在推送到 Docker Hub..." -ForegroundColor Green
docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 推送失败" -ForegroundColor Red
    exit 1
}

Write-Host "🎉 推送成功！镜像地址: ${DOCKER_USERNAME}/${IMAGE_NAME}:latest" -ForegroundColor Green