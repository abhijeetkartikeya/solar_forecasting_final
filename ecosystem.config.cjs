module.exports = {
  apps: [
    {
      name: "weather_api_v2",
      script: ".venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 8001",
      cwd: ".", // Execute from root directory
      interpreter: "none", // Since uvicorn is an executable binary
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        POSTGRES_DSN: "postgresql://solar:solar123@127.0.0.1:5445/solar",
        API_PORT: 8001
      },
      env_file: "./.env"
    },
    {
      name: "weather_frontend_v2",
      script: "npm",
      args: "run dev -- --port 5176",
      cwd: ".", // Execute from root directory
      instances: 1,
      autorestart: true,
      watch: false,
      env_file: "./.env"
    }
  ]
};
