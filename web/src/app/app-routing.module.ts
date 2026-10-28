import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CurrentRatesComponent } from './features/rates/current-rates.component';
import { ConverterComponent } from './features/converter/converter.component';

const routes: Routes = [
  { path: '', component: CurrentRatesComponent, pathMatch: 'full' },
  { path: 'converter', component: ConverterComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
