// @ts-check
import { defineConfig } from 'astro/config';

// 部署到 GitHub Pages 项目页：https://<user>.github.io/nzhongsiban/
// 如果以后换仓库名或自定义域名，改 base 即可
export default defineConfig({
  site: 'https://jaycccrrr.github.io',
  base: '/nzhongsiban',
  output: 'static',
  vite: {
    server: {
      // 允许 dev 服务器读取仓库根目录的 content/（仅开发时有用，构建不受影响）
      fs: { allow: ['..'] },
    },
  },
});
