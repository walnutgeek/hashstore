import React from 'react';
import {
  Route
} from 'react-router-dom';

import {
    Button,MenuItem,
    Toaster,Position
} from "@blueprintjs/core";

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

export const MyToaster = Toaster.create({
    className: "my-toaster",
    position: Position.TOP_RIGHT,
});