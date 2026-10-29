import { NgModule, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { BrowserModule } from '@angular/platform-browser';
import { AppRoutingModule } from './app-routing.module';
import { App } from './app.component';
import { ConverterComponent } from './features/converter/converter.component';
import { CurrentRatesComponent } from './features/rates/current-rates.component';
import { AllCurrenciesComponent } from './features/rates/all-currencies.component';
import { AnalyticsComponent } from './features/analytics/analytics.component';

@NgModule({
  declarations: [
    App,
    CurrentRatesComponent,
    ConverterComponent,
    AllCurrenciesComponent,
    AnalyticsComponent,
  ],
  imports: [BrowserModule, AppRoutingModule],
  providers: [provideBrowserGlobalErrorListeners(), provideHttpClient()],
  bootstrap: [App],
})
export class AppModule {}
