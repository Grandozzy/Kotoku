module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ["babel-preset-expo", { jsxImportSource: "nativewind" }],
      // "nativewind/babel" unconditionally loads react-native-worklets/plugin which is
      // not installed (Reanimated 4 worklets require New Arch; Android uses Old Arch).
      // We include only the css-interop transform plugin here; the JSX side is already
      // handled by jsxImportSource above (nativewind/jsx-runtime → css-interop/jsx-runtime).
    ],
    plugins: [
      require("react-native-css-interop/dist/babel-plugin").default,
      [
        "module-resolver",
        {
          root: ["./"],
          alias: {
            "@": "./src",
          },
        },
      ],
    ],
  };
};
