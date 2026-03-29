export const siteContent = {
  company: {
    name: "Peganyx",
    tagline: "Premium digital experiences engineered for trust and conversion.",
  },
  navigation: [
    { label: "Services", href: "/services" },
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
  ],
  home: {
    hero: {
      eyebrow: "Peganyx v2",
      title: "Modern company websites that look sharper and convert harder.",
      description:
        "Peganyx helps ambitious teams ship premium, trustworthy web experiences with cleaner messaging, tighter UX, and production-ready delivery.",
      primaryCta: { label: "Start a project", href: "/contact" },
      secondaryCta: { label: "Explore services", href: "/services" },
    },
    proof: [
      { label: "Launch-ready delivery", value: "Vercel-ready" },
      { label: "Execution model", value: "Fast iteration" },
      { label: "Focus", value: "Trust + conversion" },
    ],
    services: [
      {
        id: "web-redesign",
        title: "Website redesign",
        description: "Sharper positioning, stronger visual hierarchy, and cleaner conversion paths.",
      },
      {
        id: "product-marketing",
        title: "Product marketing sites",
        description: "Premium landing pages and growth-focused page systems built to ship.",
      },
      {
        id: "frontend-systems",
        title: "Frontend systems",
        description: "Maintainable Next.js foundations that support scale, reuse, and velocity.",
      },
    ],
    process: [
      { step: "01", title: "Clarify", body: "Tighten messaging, goals, proof, and audience intent." },
      { step: "02", title: "Design", body: "Craft a cleaner premium interface with stronger conversion structure." },
      { step: "03", title: "Ship", body: "Deliver a working Next.js implementation ready for preview and QA." },
    ],
    faq: [
      {
        question: "Is this Vercel-ready?",
        answer: "Yes. The backend contract uses stateless API routes suitable for Vercel deployment.",
      },
      {
        question: "Do contact submissions persist?",
        answer: "Not yet. The current MVP validates and acknowledges submissions without CRM storage.",
      },
    ],
  },
  pages: {
    services: {
      title: "Services",
      intro: "Strategy, design direction, and web implementation focused on trust and conversion.",
    },
    about: {
      title: "About Peganyx",
      intro: "A product-minded web partner for teams that need sharper presentation and cleaner execution.",
    },
    contact: {
      title: "Start a project",
      intro: "Share your goals and timeline. We’ll respond with a practical next step.",
      formFields: ["name", "email", "company", "projectType", "budget", "timeline", "message"],
    },
  },
} as const;
