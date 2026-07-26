export type ActionIconName = "download" | "copy" | "share" | "expand" | "refresh";

const PATHS: Record<ActionIconName, string> = {
  download: "M10 3v9m0 0 3.5-3.5M10 12 6.5 8.5M4 14.5V15a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-.5",
  copy: "M7.5 7.5V5.25A1.75 1.75 0 0 1 9.25 3.5h5.5A1.75 1.75 0 0 1 16.5 5.25v5.5a1.75 1.75 0 0 1-1.75 1.75H12.5M5.25 8.5h5.5a1.75 1.75 0 0 1 1.75 1.75v5.5A1.75 1.75 0 0 1 10.75 17.5h-5.5A1.75 1.75 0 0 1 3.5 15.75v-5.5A1.75 1.75 0 0 1 5.25 8.5Z",
  share: "M14.5 6.5a2 2 0 1 0-1.9-2.6L7.4 6.6a2 2 0 1 0 0 3.8l5.2 2.7a2 2 0 1 0 .6-1.3L8 9.1a2 2 0 0 0 0-.2l5.1-2.7c.36.3.83.5 1.4.5Z",
  expand: "M12.5 4.5H15.5V7.5M15.5 4.5 11.5 8.5M7.5 15.5H4.5V12.5M4.5 15.5 8.5 11.5",
  refresh: "M15.5 6.5A6 6 0 0 0 4.6 8.2M4.5 13.5A6 6 0 0 0 15.4 11.8M15.8 3.8v3.2h-3.2M4.2 16.2v-3.2h3.2",
};

export function ActionIcon({ name }: { name: ActionIconName }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path
        d={PATHS[name]}
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
