import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CurrentRatesComponent } from './features/rates/current-rates.component';
import { ConverterComponent } from './features/converter/converter.component';
import { AllCurrenciesComponent } from './features/rates/all-currencies.component';
import { AnalyticsComponent } from './features/analytics/analytics.component';

const routes: Routes = [
  { path: '', component: CurrentRatesComponent, pathMatch: 'full' },
  { path: 'converter', component: ConverterComponent },
  { path: 'all-currencies', component: AllCurrenciesComponent },
  { path: 'analytics', component: AnalyticsComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
