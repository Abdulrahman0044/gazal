import {fileURLToPath} from 'node:url';
const backend = process.env.GAZAL_BACKEND_URL || 'http://127.0.0.1:8000';
const url = new URL(backend);
if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
  throw new Error('GAZAL_BACKEND_URL must be an HTTP(S) backend origin without credentials.');
}
export default {
  output: 'standalone',
  turbopack: {root: fileURLToPath(new URL('.', import.meta.url))},
  async rewrites() {
    return [{source: '/api/:path*', destination: `${url.origin}/api/:path*`}];
  },
  async redirects() {
    return [
      ...['/admin/login', '/employee/login'].map(source => ({source, destination:'/signin', permanent:true})),
      ...['/admin/signup', '/employee/signup', '/create-account'].map(source => ({source, destination:'/signup', permanent:true}))
    ];
  },
  async headers() {
    return [{source:'/:path*', headers:[
      {key:'X-Content-Type-Options', value:'nosniff'},
      {key:'Referrer-Policy', value:'no-referrer'},
      {key:'X-Frame-Options', value:'DENY'}
    ]}];
  }
};
