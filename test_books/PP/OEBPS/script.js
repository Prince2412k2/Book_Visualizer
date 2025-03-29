
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("*").forEach(el => {
        if (el.textContent.includes('"') || el.textContent.includes('“') || el.textContent.includes('”')) {
            console.log("Matched element:", el);
            el.style.margin = "10px"; // Apply margin
            el.style.lineHeight = "1.2";
            el.style.letterSpacing = "1.2px";// ✅ Corrected (unitless value)
            
        }
    });
});

