const backendUrl = import.meta.env.VITE_BACKEND_URL;
console.log(backendUrl);

export default function Login() {
  return (
    <div className="p-4">
      <a href={`${backendUrl}/login`}>
        <button className="px-4 py-2 bg-blue-500 text-white rounded">
          Sign in with Google
        </button>
      </a>
    </div>
  );
}
