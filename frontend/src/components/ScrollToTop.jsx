// frontend/src/components/ScrollToTop.jsx

import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

// 이 컴포넌트는 UI가 없으며, 오직 스크롤 기능만 담당합니다.
function ScrollToTop() {
  // useLocation 훅을 사용해 현재 페이지의 경로(pathname) 정보를 가져옵니다.
  const { pathname } = useLocation();

  // useEffect를 사용해 pathname이 바뀔 때마다 특정 작업을 수행합니다.
  useEffect(() => {
    // pathname이 변경되었을 때 (즉, 페이지가 이동되었을 때)
    // window.scrollTo(0, 0) 명령으로 스크롤을 맨 위로 강제 이동시킵니다.
    window.scrollTo(0, 0);
  }, [pathname]); // (중요) 의존성 배열에 pathname을 넣어, 경로가 바뀔 때만 이 함수가 실행되도록 합니다.

  // 이 컴포넌트는 화면에 아무것도 그리지 않으므로 null을 반환합니다.
  return null;
}

export default ScrollToTop;