import React from 'react';
import 'prismjs/themes/prism.css';

const prismStyles = {
    C: "clike", JS: "javascript",
    PY: "python", rST: "rest",
     JAVA: "java", JSON: "json", CSS: "css",
    HTML: "markup", XML: "markup",
    SVG: "markup", HSB: "json", MD: "markdown",
    SH: "bash", YAML: "yaml"
};

const Prism = require('prismjs/components/prism-core');
Object.keys(prismStyles).forEach(
    (n)=> require(`prismjs/components/prism-${prismStyles[n]}`)
);

const Text = {
    accept_types:  ["TXT","LOG","CSV","WDF",
                ...Object.keys(prismStyles)],

    render({info, content}) {
        let prismStyle = prismStyles[info.type];
        if (prismStyle) {
            const markup = {__html: Prism.highlight(content, Prism.languages[prismStyle])}
            return <pre dangerouslySetInnerHTML={markup} />;
        } else {
            return <pre>{content||''}</pre>;
        }
    }
};
export default Text;
