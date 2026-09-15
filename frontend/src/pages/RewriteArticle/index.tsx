import { Navigate } from 'react-router-dom';

export default function RewriteArticle() {
  return <Navigate to="/dashboard" replace />;
}
