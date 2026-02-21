export const dynamic = "force-dynamic";

export default function NotFound() {
  return (
    <div style={{ 
      display: "flex", 
      flexDirection: "column", 
      alignItems: "center", 
      justifyContent: "center",
      height: "100vh",
      fontFamily: "system-ui, sans-serif"
    }}>
      <h2>404 - Not Found</h2>
      <p>Could not find requested resource</p>
    </div>
  );
}
