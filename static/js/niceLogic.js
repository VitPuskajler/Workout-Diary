"use strict";

const aboutBg = document.querySelector('.p-4.mb-3.bg-body-tertiary.rounded');
const superInfoOne = document.querySelector(".d-flex.flex-column.flex-lg-row.gap-3.align-items-start.align-items-lg-center.py-3.link-body-emphasis.text-decoration-none.border-top");
const superInfoTwo = document.querySelector(".d-flex.flex-column.flex-lg-row.gap-3.align-items-start.align-items-lg-center.py-3.link-body-emphasis.text-decoration-none.border-top.b");
const superInfoThree = document.querySelector(".d-flex.flex-column.flex-lg-row.gap-3.align-items-start.align-items-lg-center.py-3.link-body-emphasis.text-decoration-none.border-top.c"); 

aboutBg.addEventListener("mousemove", () => {
    aboutBg.classList.replace('bg-body-tertiary', 'bg-secondary');
});
aboutBg.addEventListener("mouseleave", () => {
    aboutBg.classList.replace('bg-secondary', 'bg-body-tertiary');
});

// A - Super Informations - change color when mouse on 
superInfoOne.addEventListener("mousemove", () => {
    superInfoOne.classList.add("newInformations");
});

superInfoOne.addEventListener("mouseleave", () => {
    superInfoOne.classList.remove("newInformations");
});

// B 
superInfoTwo.addEventListener("mousemove", e => {
    superInfoTwo.classList.add("newInformations");
});

superInfoTwo.addEventListener("mouseleave", () => {
    superInfoTwo.classList.remove("newInformations");
});

// C
superInfoThree.addEventListener("mousemove", e => {
    superInfoThree.classList.add("newInformations");
});

superInfoThree.addEventListener("mouseleave", () => {
    superInfoThree.classList.remove("newInformations");
});

