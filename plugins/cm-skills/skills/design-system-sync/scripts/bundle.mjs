import { createRequire } from 'module';
const { build } = createRequire(process.env.REPO + '/package.json')('esbuild');
const [entry, out] = process.argv.slice(2);
const globals = { 'react': 'React', 'react-dom': 'ReactDOM', 'react-dom/client': 'ReactDOM' };
const plugin = { name: 'globals', setup(b) {
  b.onResolve({ filter: /^(react|react-dom|react-dom\/client|react\/jsx-runtime|react\/jsx-dev-runtime)$/ }, a => ({ path: a.path, namespace: 'g' }));
  b.onLoad({ filter: /.*/, namespace: 'g' }, a => {
    if (a.path.startsWith('react/jsx')) return { contents: `const R=window.React;function j(t,p,k){const {children,...r}=p||{};if(k!==undefined)r.key=k;return Array.isArray(children)?R.createElement(t,r,...children):children===undefined?R.createElement(t,r):R.createElement(t,r,children)}module.exports={jsx:j,jsxs:j,jsxDEV:j,Fragment:R.Fragment};`, loader: 'js' };
    return { contents: `module.exports=window.${globals[a.path]};`, loader: 'js' };
  });
}};
await build({ entryPoints: [entry], outfile: out, bundle: true, format: 'iife', globalName: process.env.GLOBAL || 'Chartmetric', minify: true,
  define: { 'process.env.NODE_ENV': '"production"' }, plugins: [plugin], loader: { '.css': 'empty' }, charset: 'utf8', legalComments: 'none', logLevel: 'warning' });
