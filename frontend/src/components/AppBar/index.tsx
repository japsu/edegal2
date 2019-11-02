import React from 'react';
import { Link } from 'react-router-dom';

import Config from '../../Config';
import Album from '../../models/Album';

import './index.css';
import { T, TranslationFunction } from '../../translations';
import Breadcrumb from '../../models/Breadcrumb';

const breadcrumbSeparator = ' » ';

export interface AppBarAction {
  label: string;
  onClick?(): void;
}

interface AppBarProps {
  album: Album;
  actions?: AppBarAction[];
}

function getBreadcrumbTitle(breadcrumb: Breadcrumb, t: TranslationFunction<{ photographers: string }>) {
  switch (breadcrumb.path) {
    case '/photographers':
      return t(r => r.photographers);
    default:
      return breadcrumb.title;
  }
}

const AppBar: React.FC<AppBarProps> = ({ album, actions }) => {
  const t = T(r => r.AppBar);
  const { path, title, breadcrumb } = album;
  const fullBreadcrumb = breadcrumb.concat([{ path, title }]);
  const rootNavLinks = [
    {
      path: '/photographers',
      title: t(r => r.photographers),
    },
  ];

  document.title = fullBreadcrumb.map(crumb => getBreadcrumbTitle(crumb, t)).join(breadcrumbSeparator);

  const rootAlbum = fullBreadcrumb.shift();

  return (
    <nav className="AppBar navbar navbar-expand-md navbar-dark navbar-fixed-top">
      <Link className="navbar-brand" to={rootAlbum!.path}>
        {rootAlbum!.title}
      </Link>
      <button
        className="navbar-toggler"
        type="button"
        data-toggle="collapse"
        data-target="#AppBar-navbar"
        aria-controls="AppBar-navbar"
        aria-expanded="false"
        aria-label="Toggle navigation"
      >
        <span className="navbar-toggler-icon" />
      </button>
      <div className="collapse navbar-collapse" id="AppBar-navbar">
        {breadcrumb.length ? (
          <ul className="navbar-nav mr-auto">
            {fullBreadcrumb.map(item => (
              <li key={item.path} className="nav-item">
                <Link className="nav-link" to={item.path}>
                  {breadcrumbSeparator}
                  {getBreadcrumbTitle(item, t)}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <ul className="navbar-nav mr-auto">
            {rootNavLinks.map(item => (
              <li key={item.path} className="nav-item">
                <Link className="nav-link" to={item.path}>
                  {item.title}
                </Link>
              </li>
            ))}
          </ul>
        )}
        <ul className="navbar-nav">
          {(actions || []).map(action => (
            <li key={action.label} className="nav-item">
              <button className="btn btn-link nav-link" onClick={action.onClick}>
                {action.label}
              </button>
            </li>
          ))}
          <li className="nav-item">
            <a href={Config.loginUrl} className="nav-link AppBar-adminLink">
              {t(r => r.adminLink)}
            </a>
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default AppBar;
