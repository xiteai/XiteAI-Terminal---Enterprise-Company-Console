// One quiet line-icon set, drawn on a 20x20 grid at 1.6px. Every icon in the
// console comes from here so weights and corners always match.
const P = {
  overview: "M3 3.5h5.5V9H3zM11.5 3.5H17V7h-5.5zM11.5 10H17v6.5h-5.5zM3 12h5.5v4.5H3z",
  installs: "M2.5 4.5h15v9h-15zM7 16.5h6M10 13.5v3",
  releases: "M10.5 2.5 17.5 9.5 10 17 3 10V3.5a1 1 0 0 1 1-1zM6.8 6.8h.01",
  support: "M10 17.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM10 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM4.7 4.7l3.2 3.2M12.1 12.1l3.2 3.2M15.3 4.7l-3.2 3.2M7.9 12.1l-3.2 3.2",
  people: "M7.5 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2 17c0-3 2.5-5 5.5-5s5.5 2 5.5 5M13 3.3a3 3 0 0 1 0 5.4M15 12.2c1.8.6 3 2.4 3 4.8",
  requests: "M3 5.5h14v9.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zM3 5.5l7 5.5 7-5.5M6 2.5h8",
  access: "M10 2.5 16.5 5v5c0 4-2.8 6.5-6.5 7.5C6.3 16.5 3.5 14 3.5 10V5zM7.2 10l2 2 3.8-4",
  audit: "M5 2.5h7.5L16 6v11.5H5zM12.5 2.5V6H16M7.5 9.5h6M7.5 12.5h6M7.5 15h3.5",
  account: "M10 9.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM3.5 17.5c0-3.3 2.9-5.5 6.5-5.5s6.5 2.2 6.5 5.5",
  bell: "M5 8a5 5 0 0 1 10 0c0 5 2 6 2 6H3s2-1 2-6M8.3 17a1.8 1.8 0 0 0 3.4 0",
  search: "M9 15a6 6 0 1 0 0-12 6 6 0 0 0 0 12ZM17 17l-3.8-3.8",
  sun: "M10 13.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM10 1.8v1.7M10 16.5v1.7M3.5 3.5l1.2 1.2M15.3 15.3l1.2 1.2M1.8 10h1.7M16.5 10h1.7M3.5 16.5l1.2-1.2M15.3 4.7l1.2-1.2",
  moon: "M16.5 12.3A7 7 0 0 1 7.7 3.5a7 7 0 1 0 8.8 8.8Z",
  system: "M2.5 4h15v9.5h-15zM7 17h6M10 13.5V17",
  logout: "M8 3.5H4.5v13H8M12.5 6.5 16 10l-3.5 3.5M16 10H8",
  chevronRight: "M8 5l5 5-5 5",
  chevronLeft: "M12 5l-5 5 5 5",
  chevronDown: "M5 8l5 5 5-5",
  chevronUp: "M5 12l5-5 5 5",
  x: "M5 5l10 10M15 5 5 15",
  check: "M4.5 10.5l3.5 3.5 7.5-8",
  plus: "M10 4v12M4 10h12",
  alert: "M10 2.8 18 17H2zM10 8v4M10 14.5h.01",
  info: "M10 17.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM10 9v5M10 6.3h.01",
  download: "M10 3v10M5.5 8.5 10 13l4.5-4.5M3.5 16.5h13",
  lock: "M5 9h10v8H5zM7 9V6.5a3 3 0 0 1 6 0V9",
  key: "M7 13.5a3.5 3.5 0 1 1 3.3-4.7L17 8.8V11h-2v2h-2.2l-2.6-.5A3.5 3.5 0 0 1 7 13.5ZM6.5 10h.01",
  clock: "M10 17.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM10 6v4.2l2.8 1.8",
  filter: "M3 4.5h14l-5.5 6.5v5l-3 1.5V11z",
  eye: "M1.8 10S5 4 10 4s8.2 6 8.2 6-3.2 6-8.2 6-8.2-6-8.2-6ZM10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z",
  trash: "M3.5 5.5h13M8 5.5V3.5h4v2M5 5.5l.8 11h8.4l.8-11M8.5 8.5v5M11.5 8.5v5",
  arrowRight: "M4 10h12M11.5 5.5 16 10l-4.5 4.5",
  arrowLeft: "M16 10H4M8.5 5.5 4 10l4.5 4.5",
  arrowUp: "M10 16V4M5.5 8.5 10 4l4.5 4.5",
  more: "M4.5 10h.01M10 10h.01M15.5 10h.01",
  external: "M11.5 3.5h5v5M16.5 3.5 9 11M14 11.5v5h-10v-10h5",
  mail: "M2.5 4.5h15v11h-15zM2.5 5l7.5 6 7.5-6",
  phone: "M5.5 2.5h3l1.5 4-2 1.3a9 9 0 0 0 4.2 4.2l1.3-2 4 1.5v3a1.5 1.5 0 0 1-1.6 1.5A14 14 0 0 1 4 4.1 1.5 1.5 0 0 1 5.5 2.5Z",
  pin: "M10 17.5s5.5-5 5.5-9.5a5.5 5.5 0 0 0-11 0c0 4.5 5.5 9.5 5.5 9.5ZM10 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
  briefcase: "M2.5 6h15v10h-15zM7 6V3.5h6V6M2.5 10.5h15",
  cap: "M10 3.5 18 7.5l-8 4-8-4zM5 9v4c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5V9M18 7.5v4.5",
  link: "M8.5 11.5a3.5 3.5 0 0 0 5 0l2.5-2.5a3.5 3.5 0 0 0-5-5l-1 1M11.5 8.5a3.5 3.5 0 0 0-5 0L4 11a3.5 3.5 0 0 0 5 5l1-1",
  sparkle: "M10 2.5 11.6 8.4 17.5 10l-5.9 1.6L10 17.5l-1.6-5.9L2.5 10l5.9-1.6z",
  refresh: "M16.5 10a6.5 6.5 0 1 1-2-4.7M16.5 3.5V7H13",
  laptop: "M4 5h12v8H4zM2 15.5h16",
  desktop: "M2.5 3.5h15v10h-15zM7.5 17h5M10 13.5V17",
  tablet: "M5 2.5h10v15H5zM9 15h2",
  command: "M7 7V5a2 2 0 1 0-2 2h10a2 2 0 1 0-2-2v10a2 2 0 1 0 2-2H5a2 2 0 1 0 2 2V7",
  org: "M8 2.5h4v3.5H8zM3 14h4v3.5H3zM13 14h4v3.5h-4zM10 6v4M5 14v-4h10v4",
  activity: "M2.5 10h3l2.5-5.5 4 11 2.5-5.5h3",
  calendar: "M3 4.5h14v12.5H3zM3 8.5h14M7 2.5v4M13 2.5v4",
  heart: "M10 16.5S3 12.5 3 7.5A3.5 3.5 0 0 1 10 6a3.5 3.5 0 0 1 7 1.5c0 5-7 9-7 9Z",
  user: "M10 9.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM3.5 17.5c0-3.3 2.9-5.5 6.5-5.5s6.5 2.2 6.5 5.5",
  circleCheck: "M10 17.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM6.8 10.2l2.2 2.2 4.2-4.6",
  circleX: "M10 17.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM7.5 7.5l5 5M12.5 7.5l-5 5",
  pause: "M7 4.5v11M13 4.5v11",
  hourglass: "M5.5 2.5h9M5.5 17.5h9M6.5 2.5c0 4 7 4 7 7.5s-7 3.5-7 7.5M13.5 2.5c0 4-7 4-7 7.5s7 3.5 7 7.5",
  send: "M3 10 17 3l-4.5 14-3-5.5z",
  panel: "M3 3.5h14v13H3zM8 3.5v13",
  edit: "M12.5 4.5l3 3L7 16H4v-3zM11 6l3 3",
  chevronsUpDown: "M6.5 7.5 10 4l3.5 3.5M6.5 12.5 10 16l3.5-3.5",
  home: "M3 9.5 10 3.5l7 6V17H3zM8 17v-5h4v5",
  grid: "M3.5 3.5h5v5h-5zM11.5 3.5h5v5h-5zM3.5 11.5h5v5h-5zM11.5 11.5h5v5h-5z",
  menu: "M3 5.5h14M3 10h14M3 14.5h14",
  browser: "M2.5 4h15v12h-15zM2.5 7.5h15M5 5.8h.01M7 5.8h.01",
  box: "M10 2.5 17 6v8l-7 3.5L3 14V6zM3 6l7 3.5L17 6M10 9.5v8",
  code: "M6.5 6 2.5 10l4 4M13.5 6l4 4-4 4M11.5 3.5l-3 13",
  branch: "M6 3v9.5M6 12.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5ZM14 7.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM14 7.5c0 4-8 3-8 5",
  folder: "M2.5 5.5a1 1 0 0 1 1-1h4l1.5 2h7.5a1 1 0 0 1 1 1V15a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1z",
  file: "M5 2.5h6.5L15 6v11.5H5zM11.5 2.5V6H15",
  globe: "M10 17.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM2.5 10h15M10 2.5c2 2.2 3 4.7 3 7.5s-1 5.3-3 7.5c-2-2.2-3-4.7-3-7.5s1-5.3 3-7.5Z",
};

export default function Icon({ name, size = 18, stroke = 1.6, className, title }) {
  const d = P[name];
  if (!d) return null;
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
    >
      {title && <title>{title}</title>}
      <path d={d} />
    </svg>
  );
}
