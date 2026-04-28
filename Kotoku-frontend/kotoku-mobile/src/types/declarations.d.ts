// Allow TypeScript to accept CSS imports (used by NativeWind global.css)
declare module "*.css" {
  const content: unknown;
  export default content;
}
