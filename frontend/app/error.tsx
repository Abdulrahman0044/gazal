'use client';
export default function ErrorPage({reset}:{reset:()=>void}) {
  return <main style={{fontFamily:'system-ui',padding:'4rem'}}><h1>Something went wrong</h1><p>Please try loading this page again.</p><button onClick={reset}>Try again</button><a href="/"> Home</a></main>;
}
