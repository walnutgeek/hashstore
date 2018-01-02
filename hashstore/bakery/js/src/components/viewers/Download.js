import React from 'react';
import {Icon} from "../common_components";

const Download = {
    render({path}) {
        return (
            <div>
                <a href={`/.get/data/${path.aliasPath.toUrl()}`} download>
                    <Icon iconName="download" />
                </a>
            </div>);
    }
};
export default Download;
