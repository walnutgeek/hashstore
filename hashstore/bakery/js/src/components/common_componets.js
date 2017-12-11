import React from 'react';
import {
  Route
} from 'react-router-dom';

import {Button,MenuItem} from "@blueprintjs/core";

const createOnClicker = (OnClicker) => (
    ({to, children, ...props}) => (
        <Route render={({history}) => (
            <OnClicker onClick={ () => history.push(to) } {...props}>
                {children}
            </OnClicker>
        )}/>
    )
);

export const ToButton = createOnClicker(Button);
export const ToMenuItem = createOnClicker(MenuItem);

export const Icon = ({iconName}) => (
    <span className={`pt-icon pt-icon-${iconName}`}></span>);
