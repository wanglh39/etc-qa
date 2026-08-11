/// <reference types="vite/client" />

declare module '*.vue' {
  // 【修改点】去掉 "type"，改为普通导入，确保组件被视为一个值
  import { DefineComponent } from 'vue' 
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/ban-types
  const component: DefineComponent<{}, {}, any>
  export default component
}