/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Lint se ejecuta en CI por separado; no bloquea el build del MVP.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
