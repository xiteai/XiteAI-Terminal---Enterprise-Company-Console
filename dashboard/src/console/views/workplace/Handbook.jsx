import Card from "../../../components/Card.jsx";
import PageHeader from "../../../components/PageHeader.jsx";

// How the company works, written down. Content, not data: it lives here until
// there's a reason for anyone to edit it from the console.
const SECTIONS = [
  {
    title: "Leave",
    body: [
      "Annual leave is 18 days a year and has to be asked for before it starts. Sick and casual leave can be filed after the fact, up to 30 days back.",
      "Weekends are never counted against your balance. A pending request already holds its days, so your balance is what's genuinely left.",
      "Your manager, or anyone above your level who can decide leave, approves it.",
    ],
  },
  {
    title: "Expenses",
    body: [
      "Claim anything you spent on the company's behalf, up to ₹2,00,000 in one claim. Split anything larger.",
      "Claims close six months after the money was spent. Say what it was for — 'client dinner, Mumbai' beats 'food'.",
    ],
  },
  {
    title: "Equipment",
    body: [
      "Ask for what you need to do the job through Assets. Up to ten of anything; more than that needs a conversation first.",
      "Broken kit is a helpdesk ticket, not an asset request.",
    ],
  },
  {
    title: "Getting help",
    body: [
      "Anything technical goes to the Helpdesk — laptops, access, software, the VPN. Say when it started and what you already tried.",
      "Urgent means someone can't work right now. Everything else is normal.",
    ],
  },
  {
    title: "Pay",
    body: [
      "Payslips appear under Pay once payroll issues them. You always see your own; seeing anyone else's takes a level above theirs and the right permission.",
    ],
  },
];

export default function Handbook() {
  return (
    <div className="stack">
      <PageHeader title="Handbook" subtitle="How we work, in the short version." />
      <div className="wp-handbook">
        {SECTIONS.map((s) => (
          <Card key={s.title} title={s.title}>
            {s.body.map((p) => <p key={p} className="wp-para">{p}</p>)}
          </Card>
        ))}
      </div>
    </div>
  );
}
