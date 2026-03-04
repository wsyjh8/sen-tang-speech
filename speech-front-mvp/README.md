# Speech Front MVP

Next.js 前端 MVP，用于调用后端 API 并展示 JSON 报告结果。

## 运行方式

```bash
npm install
npm run dev
```

打开 **http://localhost:3000/practice**

## 技术栈

- Next.js 16.1.x (App Router)
- React 19.2.1
- TypeScript 5.9.x
- Tailwind CSS 4.2.1
- Zustand 5.0.11 (状态管理)
- React Query 5.90.21
- Zod 4.3.6 (Schema 验证)
- Recharts 3.7.0 (图表)

## 环境变量

`.env.local`:
```
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_AUDIO_PATH=D:/code/AI/startUp/sen-tang-speech/mvp/phase1_test/artifacts/test_16k.wav
```

## 页面

- `/practice` - 练习页，点击按钮拉取 demo 报告
- `/report` - 报告展示页
- `/processing` - 处理中占位页

## API

前端通过 `/api` 代理转发到后端：
```
/api/pipeline/step1_6_demo?audio=<音频路径>&use_llm=0
```
