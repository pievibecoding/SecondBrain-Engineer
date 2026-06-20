import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function Layout() {
  const { currentUser, isAdmin, logout } = useAuth();
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/chat">SecondBrain</Link>
        <nav>
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/wiki">Wiki</NavLink>
          <NavLink to="/graph">Graph</NavLink>
          {isAdmin ? <NavLink to="/admin/nas-queue">Admin</NavLink> : null}
        </nav>
        <div className="user-menu">
          {currentUser ? <span>{currentUser.email}</span> : null}
          {currentUser ? <button className="secondary" type="button" onClick={logout}>Logout</button> : null}
        </div>
      </header>
      <main className="page"><Outlet /></main>
    </div>
  );
}
