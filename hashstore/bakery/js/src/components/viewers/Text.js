import React from 'react';
import 'prismjs/themes/prism.css';


const prismStyles = {
    C: "clike", JS: "javascript",
    PY: "python", rST: "rest",
    JAVA: "java", JSON: "json",
    CSS: "css", HTML: "markup",
    XML: "markup", SVG: "markup",
    HSB: "json", MD: "markdown",
    SH: "bash", YAML: "yaml"
};

const Prism = require('prismjs/components/prism-core');
Object.keys(prismStyles).forEach(
    (n)=> require(`prismjs/components/prism-${prismStyles[n]}`)
);

const prismTypes = Object.keys(prismStyles);

const Text = {
    accept_types:  ["TXT","LOG","CSV","WDF",
                ...prismTypes],

    render({info, content}) {
        try {
            let lang = prismStyles[info.file_type];
            if (lang && content) {
                const grammar = Prism.languages[lang];
                const __html = Prism.highlight(content, grammar, lang);
                return <pre dangerouslySetInnerHTML={{__html}} />;
            }
        }catch (e){
            console.log(e);
        }
        return <pre>{content||''}</pre>;
    }
};
export default Text;
