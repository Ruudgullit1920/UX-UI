export default function Icon({ name, size = 20, ...props }) {
  const paths = {
    website: <><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18M7 6.5h.01M10 6.5h.01"/></>,
    screenshot: <><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/></>,
    mobile: <><rect x="6" y="2" width="12" height="20" rx="3"/><path d="M10 5h4M11 19h2"/></>,
    figma: <><rect x="4" y="3" width="7" height="7" rx="2"/><rect x="13" y="3" width="7" height="7" rx="2"/><rect x="4" y="12" width="7" height="9" rx="2"/><circle cx="16.5" cy="15.5" r="3.5"/></>,
    arrow: <path d="M5 12h14m-5-5 5 5-5 5"/>,
    check: <path d="m5 12 4 4L19 6"/>,
    close: <path d="m6 6 12 12M6 18 18 6"/>,
    upload: <path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/>,
    report: <path d="M14 3H5v18h14V8Zm0 0v5h5M8 12h8M8 16h5"/>,
    sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.report}</svg>;
}
