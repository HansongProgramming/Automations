// 1. Get all merged rows
const incomingArray = $('Merge').all().map(i => i.json);

// 2. Clean + structured SOP generator
function dynamicSOP(data) {
  const sop = {
    gen: { faq: [] },
    svc: { 
      list: [], 
      price: {}, 
      duration_mins: {}, 
      stylist: {} 
    },
    book: {},
    team: {},
    policy: {}
  };

  data.forEach(item => {
    // ---------------------
    // SERVICES
    // ---------------------
    if (item.Services && item.Price && item.Duration && item.Stylist) {
      const svcName = String(item.Services).trim();

      // Add to list
      if (!sop.svc.list.includes(svcName)) {
        sop.svc.list.push(svcName);
      }

      // Price → number
      sop.svc.price[svcName] = Number(
        String(item.Price).replace(/[^0-9.]/g, "")
      ) || 0;

      // Duration → minutes
      const dur = String(item.Duration).toLowerCase();
      let mins = 0;

      const h = dur.match(/(\d+)\s*h/);
      const m = dur.match(/(\d+)\s*m/);

      if (h) mins += Number(h[1]) * 60;
      if (m) mins += Number(m[1]);

      sop.svc.duration_mins[svcName] = mins;
      sop.svc.stylist[svcName] = String(item.Stylist).trim();
    }

    // ---------------------
    // FAQ
    // ---------------------
    if (item.Question && item.Answer) {
      sop.gen.faq.push({
        question: String(item.Question).trim(),
        answer: String(item.Answer).trim()
      });
    }
  });

  return sop;
}

// 3. Run parser
return dynamicSOP(incomingArray);
