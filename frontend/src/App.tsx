import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import CaseDetail from './pages/CaseDetail';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/case/:caseId" element={<CaseDetail />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
