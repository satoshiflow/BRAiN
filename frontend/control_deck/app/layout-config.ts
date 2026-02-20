// Force all pages to be dynamic (no static generation)
// This prevents useContext errors during build
export const dynamic = 'force-dynamic';
export const dynamicParams = true;
export const revalidate = 0;
