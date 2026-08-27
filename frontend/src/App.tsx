import { BrowserRouter, Link, Navigate, NavLink, useLocation, useRoutes, type RouteObject } from "react-router-dom";

import AddJobPage from "./AddJobPage";
import AnalyzeJobPage from "./AnalyzeJobPage";
import { APP_PATHS } from "./app-route-paths";
import DiscoverPage from "./DiscoverPage";
import JobDetailPage from "./JobDetailPage";
import JobsPage from "./JobsPage";
import ProfilePage from "./ProfilePage";
import PlanPage from "./PlanPage";

export function AppNavigation() {
  const location = useLocation();
  return <header className="app-navigation"><nav>
    <Link className="brand" to="/">Job<span>Pilot</span></Link>
    <div className="nav-links">
      <NavLink className={({ isActive }) => isActive || location.pathname === "/" ? "active" : undefined} to="/analyze">岗位分析</NavLink>
      <NavLink className={({ isActive }) => isActive || location.pathname.startsWith("/jobs/") ? "active" : undefined} to="/my-jobs">我的岗位</NavLink>
      <NavLink to="/plan">计划</NavLink>
      <NavLink to="/profile">求职档案</NavLink>
    </div>
  </nav></header>;
}

const APP_ROUTES: RouteObject[] = [
  { path: APP_PATHS.home, element: <AnalyzeJobPage /> },
  { path: APP_PATHS.analyze, element: <AnalyzeJobPage /> },
  { path: APP_PATHS.discover, element: <DiscoverPage /> },
  { path: APP_PATHS.myJobs, element: <JobsPage /> },
  { path: APP_PATHS.legacyJobs, element: <Navigate to={APP_PATHS.myJobs} replace /> },
  { path: APP_PATHS.addJob, element: <AddJobPage /> },
  { path: APP_PATHS.jobDetail, element: <JobDetailPage /> },
  { path: APP_PATHS.profile, element: <ProfilePage /> },
  { path: APP_PATHS.plan, element: <PlanPage /> },
  { path: "*", element: <Navigate to="/" replace /> },
];

export function AppRoutes() { return useRoutes(APP_ROUTES); }

export default function App() {
  return <BrowserRouter><AppNavigation /><AppRoutes /><footer className="global-footer"><span>JobPilot</span><span>基于真实经历的岗位匹配与简历优化</span></footer></BrowserRouter>;
}
