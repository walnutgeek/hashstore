import React from 'react';
import MarkdownIt from 'markdown-it';
const md = new MarkdownIt();

const Markdown = {
    accept_types:  ["MD"],

    render({info, content}) {
        try {
            if(content){
                const __html = md.render(content);
                return <div dangerouslySetInnerHTML={{__html}} /> ;
            }
        }catch(e){}
        return <div/>;
    }
};

export default Markdown;
