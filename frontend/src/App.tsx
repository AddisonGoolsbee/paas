import { useEffect, useState } from "react";
import Terminal from "./components/Terminal";
import Login from "./components/Login";

const backendUrl = import.meta.env.VITE_BACKEND_URL;

function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${backendUrl}/me`, {
      credentials: "include",
    }).then(async (res) => {
      setAuthed(res.ok);
    });
  }, []);

  if (authed === null) return <div>Loading...</div>;
  return authed ? <Terminal /> : <Login />;
}

export default App;
